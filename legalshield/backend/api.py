"""
LegalShield Backend API — FastAPI server

iOS アプリ（JapaneseLegalRAG.swift / LLMService.swift）からの HTTP 呼出を受ける。
Windows 機（RTX 4080, 100.76.218.124:8000）で uvicorn 経由で起動する。

【エンドポイント】

  GET  /health                     — ヘルスチェック
  POST /rag/query                  — 判例検索 + LLM 回答（rag_query 相当）
  POST /rag/retrieve               — 判例検索のみ（top-K chunks）
  POST /rag/statutes               — 法令検索（domain で絞込み）
  POST /rag/partners               — パートナー機関検索（弁護士会・NGO・支援センター）
  POST /api/generate               — Ollama proxy（CloudOllamaProvider.swift 互換）
  POST /api/chat                   — Ollama chat proxy

【起動方法（Windows）】

  PS> cd D:\\projects\\LegalShield
  PS> .\\.venv\\Scripts\\Activate.ps1
  PS> uvicorn legalshield.backend.api:app --host 0.0.0.0 --port 8000 --workers 2

iOS の LLMSettings 既定エンドポイントは http://100.76.218.124:8000
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import lancedb
import pandas as pd
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import harness

logger = logging.getLogger("legalshield.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

# ----------------------------------------------------------------------------
# 設定
# ----------------------------------------------------------------------------

# Windows 既定パス。Mac で起動時は環境変数で上書き可能。
DB_PATH = Path(os.environ.get("LEGALSHIELD_LANCEDB", r"D:\projects\LegalShield\lancedb"))
SEEDS_DIR = Path(os.environ.get("LEGALSHIELD_SEEDS", str(Path(__file__).resolve().parents[1] / "knowledge" / "seeds")))
OLLAMA_URL = os.environ.get("LEGALSHIELD_OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL_NAME = os.environ.get("LEGALSHIELD_EMBED_MODEL", "intfloat/multilingual-e5-small")
DEFAULT_LLM = os.environ.get("LEGALSHIELD_DEFAULT_LLM", "gemma3:27b")
DEFAULT_K = 8

# L7 監査ログ（SHA-256 chain）の保存先
AUDIT_LOG_PATH = Path(os.environ.get(
    "LEGALSHIELD_AUDIT_LOG",
    str(Path(__file__).resolve().parents[1] / "lancedb" / "harness_audit.jsonl"),
))

# LanceDB tables（環境によって存在しないものもあるため、起動時に確認）
PRECEDENTS_TABLE = "precedents"
STATUTES_TABLE = "statutes"  # elaws_embed_v2 等で作成想定

# ----------------------------------------------------------------------------
# モデル lazy load（FastAPI 起動を高速化）
# ----------------------------------------------------------------------------

_embed_model = None
_lance_db = None

def get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading embedding model %s on %s ...", EMBED_MODEL_NAME, device)
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME, device=device)
    return _embed_model

def get_lance_db():
    global _lance_db
    if _lance_db is None:
        if not DB_PATH.exists():
            raise RuntimeError(f"LanceDB path not found: {DB_PATH}")
        _lance_db = lancedb.connect(str(DB_PATH))
    return _lance_db

def embed_query(text: str) -> list[float]:
    """e5 convention: prefix with 'query: '."""
    model = get_embed_model()
    vec = model.encode([f"query: {text}"], normalize_embeddings=True)[0]
    return vec.tolist()

# ----------------------------------------------------------------------------
# FastAPI app
# ----------------------------------------------------------------------------

app = FastAPI(
    title="LegalShield Backend API",
    version="1.0.0",
    description="日本法令 + 判例 + パートナー機関の検索 + Ollama proxy",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番は Tailscale IP に絞ること
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------------
# Pydantic schemas
# ----------------------------------------------------------------------------

class RagQueryRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)
    top_k: int = Field(DEFAULT_K, ge=1, le=20)
    model: Optional[str] = None
    domain: Optional[str] = None
    dedupe_cases: bool = True

class RagChunk(BaseModel):
    text: str
    score: float
    metadata: dict[str, Any]

class RagQueryResponse(BaseModel):
    answer: Optional[str]
    chunks: list[RagChunk]
    elapsed_ms: int
    model_used: Optional[str] = None

class StatutesRequest(BaseModel):
    query: str = Field(..., min_length=2)
    domain: Optional[str] = None
    top_k: int = Field(5, ge=1, le=20)

class PartnersRequest(BaseModel):
    query: str = Field(..., min_length=1)
    prefecture: Optional[str] = None
    kind: Optional[str] = None  # bar_association / ngo / support_center / hotline
    limit: int = Field(20, ge=1, le=100)

class OllamaGenerateRequest(BaseModel):
    model: str
    prompt: str
    system: Optional[str] = None
    stream: bool = False
    options: Optional[dict[str, Any]] = None

class AnswerRequest(BaseModel):
    """L1-L7 anti-hallucination harness を通した grounded 回答。"""
    question: str = Field(..., min_length=2, max_length=2000)
    top_k: int = Field(DEFAULT_K, ge=1, le=20)
    model: Optional[str] = None
    judge_model: Optional[str] = None  # 指定時は独立 LLM で cross-check（L5）
    use_statutes: bool = True
    audit: bool = True

# ----------------------------------------------------------------------------
# /health
# ----------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, Any]:
    status: dict[str, Any] = {
        "ok": True,
        "lancedb_path": str(DB_PATH),
        "lancedb_exists": DB_PATH.exists(),
        "seeds_dir": str(SEEDS_DIR),
        "seeds_exists": SEEDS_DIR.exists(),
        "ollama_url": OLLAMA_URL,
        "embed_model": EMBED_MODEL_NAME,
        "default_llm": DEFAULT_LLM,
    }
    # LanceDB のテーブル列挙（接続できる場合のみ）
    if DB_PATH.exists():
        try:
            db = get_lance_db()
            status["lancedb_tables"] = db.table_names()
        except Exception as e:
            status["lancedb_error"] = str(e)
    # Ollama 接続テスト
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        status["ollama_ok"] = r.status_code == 200
        if r.status_code == 200:
            status["ollama_models"] = [m["name"] for m in r.json().get("models", [])]
    except Exception as e:
        status["ollama_ok"] = False
        status["ollama_error"] = str(e)
    return status

# ----------------------------------------------------------------------------
# /rag/query — 判例検索 + LLM 回答（rag_query.py と等価）
# ----------------------------------------------------------------------------

SYSTEM_PROMPT_JA = """あなたは日本の法律実務に精通したアシスタントです。
提示された判例（最高裁判所・下級審）の抜粋を根拠に、ユーザーの法律質問に答えてください。

ルール:
1. 必ず提示された判例のみを根拠とし、判例外の知識で断定しない
2. 引用時は [事件番号] を末尾に付ける（例: 最判平成24年... [平成20(受)1234]）
3. 判例が質問と関連薄い場合は「直接的な判例は見当たらない」と明示
4. 結論 → 根拠判例 → 注意点 の順で構造化
5. 簡潔・実務的に。冗長な前置きは禁止
6. 最後に必ず「本回答は参考であり、具体的な法律行動は弁護士へ相談してください」を付記"""

@app.post("/rag/query", response_model=RagQueryResponse)
def rag_query(req: RagQueryRequest) -> RagQueryResponse:
    start = time.time()
    try:
        db = get_lance_db()
        if PRECEDENTS_TABLE not in db.table_names():
            raise HTTPException(404, f"precedents table not found in LanceDB ({DB_PATH})")
        table = db.open_table(PRECEDENTS_TABLE)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"LanceDB unavailable: {e}")

    # Retrieve
    qvec = embed_query(req.question)
    over_fetch = req.top_k * 3 if req.dedupe_cases else req.top_k
    rows = table.search(qvec).limit(over_fetch).to_pandas()

    # Dedupe by lawsuit_id if available
    chunks: list[RagChunk] = []
    seen_cases: set[str] = set()
    for _, row in rows.iterrows():
        case_id = str(row.get("lawsuit_id", row.get("case_id", row.name)))
        if req.dedupe_cases and case_id in seen_cases:
            continue
        seen_cases.add(case_id)
        chunks.append(RagChunk(
            text=str(row.get("text", row.get("content", ""))),
            score=float(row.get("_distance", row.get("score", 0.0))),
            metadata={k: _to_jsonable(v) for k, v in row.items() if k not in ("vector", "text", "content")},
        ))
        if len(chunks) >= req.top_k:
            break

    # Call Ollama for answer
    model_name = req.model or DEFAULT_LLM
    answer: Optional[str] = None
    try:
        context_blocks = "\n\n---\n\n".join(
            f"[{i+1}] {c.text[:1200]}" for i, c in enumerate(chunks)
        )
        user_prompt = f"【質問】\n{req.question}\n\n【参考判例（top-{len(chunks)}）】\n{context_blocks}"
        ollama_resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_JA},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=120,
        )
        if ollama_resp.status_code == 200:
            answer = ollama_resp.json().get("message", {}).get("content")
    except Exception as e:
        logger.warning("Ollama call failed: %s", e)

    return RagQueryResponse(
        answer=answer,
        chunks=chunks,
        elapsed_ms=int((time.time() - start) * 1000),
        model_used=model_name if answer else None,
    )

# ----------------------------------------------------------------------------
# /rag/retrieve — chunks のみ（LLM スキップ）
# ----------------------------------------------------------------------------

@app.post("/rag/retrieve", response_model=RagQueryResponse)
def rag_retrieve(req: RagQueryRequest) -> RagQueryResponse:
    req2 = RagQueryRequest(**{**req.model_dump(), "model": None})
    # Force-skip LLM by setting model=None
    start = time.time()
    db = get_lance_db()
    if PRECEDENTS_TABLE not in db.table_names():
        raise HTTPException(404, "precedents table not found")
    table = db.open_table(PRECEDENTS_TABLE)
    qvec = embed_query(req.question)
    rows = table.search(qvec).limit(req.top_k).to_pandas()
    chunks = [
        RagChunk(
            text=str(row.get("text", row.get("content", ""))),
            score=float(row.get("_distance", 0.0)),
            metadata={k: _to_jsonable(v) for k, v in row.items() if k not in ("vector", "text", "content")},
        )
        for _, row in rows.iterrows()
    ]
    return RagQueryResponse(answer=None, chunks=chunks, elapsed_ms=int((time.time() - start) * 1000))

# ----------------------------------------------------------------------------
# /rag/statutes — 法令検索
# ----------------------------------------------------------------------------

@app.post("/rag/statutes", response_model=RagQueryResponse)
def rag_statutes(req: StatutesRequest) -> RagQueryResponse:
    start = time.time()
    db = get_lance_db()
    if STATUTES_TABLE not in db.table_names():
        raise HTTPException(
            404,
            f"statutes table not found in LanceDB. "
            f"Run vectorize_all_datasets.py / elaws_embed_v2.py on Windows first."
        )
    table = db.open_table(STATUTES_TABLE)
    qvec = embed_query(req.query)
    rows = table.search(qvec).limit(req.top_k * 2).to_pandas()
    # optional domain filter
    if req.domain:
        rows = rows[rows.apply(lambda r: req.domain in str(r.to_dict()), axis=1)]
    rows = rows.head(req.top_k)
    chunks = [
        RagChunk(
            text=str(row.get("text", row.get("content", ""))),
            score=float(row.get("_distance", 0.0)),
            metadata={k: _to_jsonable(v) for k, v in row.items() if k not in ("vector", "text", "content")},
        )
        for _, row in rows.iterrows()
    ]
    return RagQueryResponse(answer=None, chunks=chunks, elapsed_ms=int((time.time() - start) * 1000))

# ----------------------------------------------------------------------------
# /rag/partners — 弁護士会・NGO・支援センター検索（CSV seeds から）
# ----------------------------------------------------------------------------

@app.post("/rag/partners")
def rag_partners(req: PartnersRequest) -> dict[str, Any]:
    sources = {
        "bar_association": SEEDS_DIR / "bar_associations_geocoded.csv",
        "ngo": SEEDS_DIR / "ngo_seed_geocoded.csv",
        "support_center": SEEDS_DIR / "support_centers_geocoded.csv",
        "hotline": SEEDS_DIR / "national_hotlines.csv",
        "pref_resource": SEEDS_DIR / "pref_resources.csv",
    }
    if req.kind:
        if req.kind not in sources:
            raise HTTPException(400, f"unknown kind: {req.kind}. Available: {list(sources)}")
        sources = {req.kind: sources[req.kind]}

    results: list[dict[str, Any]] = []
    for kind, path in sources.items():
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path)
        except Exception as e:
            logger.warning("Failed to load %s: %s", path, e)
            continue
        df = df.fillna("")
        # query matching: case-insensitive substring across all string columns
        q = req.query.lower()
        mask = df.apply(
            lambda row: any(q in str(v).lower() for v in row.values),
            axis=1,
        )
        if req.prefecture:
            pref_mask = df.apply(
                lambda row: req.prefecture in str(row.values),
                axis=1,
            )
            mask = mask & pref_mask
        sub = df[mask].head(req.limit)
        for _, row in sub.iterrows():
            d = {k: _to_jsonable(v) for k, v in row.items()}
            d["_kind"] = kind
            results.append(d)
    return {"count": len(results), "results": results[: req.limit]}

# ----------------------------------------------------------------------------
# /rag/answer — L1-L7 anti-hallucination harness（幻覚防止の本命）
# ----------------------------------------------------------------------------

def _row_text(row) -> str:
    return str(row.get("text", row.get("content", "")))

def _make_precedent_retriever() -> Optional[harness.RetrieveFn]:
    db = get_lance_db()
    if PRECEDENTS_TABLE not in db.table_names():
        return None
    table = db.open_table(PRECEDENTS_TABLE)

    def _retrieve(question: str, k: int) -> list[harness.Source]:
        qvec = embed_query(question)
        rows = table.search(qvec).limit(k * 3).to_pandas()
        out: list[harness.Source] = []
        seen: set[str] = set()
        for _, row in rows.iterrows():
            case_id = str(row.get("lawsuit_id", row.get("case_number", row.name)))
            if case_id in seen:
                continue
            seen.add(case_id)
            cn = str(row.get("case_number", "") or "")
            court = str(row.get("court_name", "") or "")
            out.append(harness.Source(
                id="", kind="precedent", text=_row_text(row),
                score=float(row.get("_distance", 0.0) or 0.0),
                trust="high", provenance="precedent_db",
                citation=(cn or court or "判例"),
                metadata={"case_number": cn, "court": court},
            ))
            if len(out) >= k:
                break
        return out
    return _retrieve

def _make_statute_retriever() -> Optional[harness.RetrieveFn]:
    db = get_lance_db()
    if STATUTES_TABLE not in db.table_names():
        return None
    table = db.open_table(STATUTES_TABLE)

    def _retrieve(question: str, k: int) -> list[harness.Source]:
        qvec = embed_query(question)
        rows = table.search(qvec).limit(k).to_pandas()
        out: list[harness.Source] = []
        for _, row in rows.iterrows():
            title = str(row.get("title", row.get("law_name", "")) or "")
            article = str(row.get("article", row.get("article_number", "")) or "")
            label = (f"{title}{article}").strip() or "法令"
            out.append(harness.Source(
                id="", kind="statute", text=_row_text(row),
                score=float(row.get("_distance", 0.0) or 0.0),
                trust="high", provenance="statute_db",
                citation=label,
                metadata={"title": title, "article": article},
            ))
        return out
    return _retrieve

def _make_ollama_chat(model_name: str) -> harness.LlmChat:
    def _chat(system: str, user: str, temperature: float) -> str:
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {"temperature": temperature, "num_ctx": 8192},
            },
            timeout=180,
        )
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "") or ""
    return _chat

@app.post("/rag/answer")
def rag_answer(req: AnswerRequest) -> dict[str, Any]:
    """検索ゲートを構造的に強制した grounded 回答（幻覚防止 harness）。

    iOS / 外部 agent は通常の法律 QA でこのエンドポイントを使うこと。
    生の /api/generate（無検索）を法律質問に使うと幻覚するため非推奨。
    """
    try:
        get_lance_db()
    except Exception as e:
        raise HTTPException(503, f"LanceDB unavailable: {e}")

    model_name = req.model or DEFAULT_LLM
    precedent_fn = _make_precedent_retriever()
    statute_fn = _make_statute_retriever() if req.use_statutes else None
    llm_chat = _make_ollama_chat(model_name)
    judge_chat = _make_ollama_chat(req.judge_model) if req.judge_model else None

    result = harness.run_harness(
        req.question,
        retrieve_precedents=precedent_fn,
        retrieve_statutes=statute_fn,
        llm_chat=llm_chat,
        judge_chat=judge_chat,
        top_k=req.top_k,
        audit_path=AUDIT_LOG_PATH if req.audit else None,
    )
    result["model_used"] = model_name
    return result

# ----------------------------------------------------------------------------
# /api/generate — Ollama proxy（CloudOllamaProvider.swift 互換）
# ----------------------------------------------------------------------------

@app.post("/api/generate")
def ollama_generate(req: OllamaGenerateRequest) -> dict[str, Any]:
    """iOS の CloudOllamaProvider が直接叩く既存形式。"""
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=req.model_dump(exclude_none=True),
            timeout=120,
        )
        if r.status_code != 200:
            raise HTTPException(r.status_code, f"Ollama error: {r.text[:500]}")
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(503, f"Ollama unavailable: {e}")

@app.post("/api/chat")
def ollama_chat(payload: dict[str, Any]) -> dict[str, Any]:
    """Ollama chat passthrough."""
    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
        if r.status_code != 200:
            raise HTTPException(r.status_code, f"Ollama error: {r.text[:500]}")
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(503, f"Ollama unavailable: {e}")

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _to_jsonable(v: Any) -> Any:
    """numpy / pandas 型を JSON シリアライズ可能にする。"""
    try:
        import numpy as np
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
        if isinstance(v, (np.bool_,)):
            return bool(v)
        if isinstance(v, np.ndarray):
            return v.tolist()
    except ImportError:
        pass
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", errors="replace")
    if pd.isna(v) if not isinstance(v, (list, dict)) else False:
        return None
    return v
