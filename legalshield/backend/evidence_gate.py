"""Evidence Gate — harness L0 層。

接地原則 §2.5（追加）: 任意の案件分析前、利用者証拠フォルダの完全索引が必須。
未索引の状態で L1 以降に進むことを構造的に禁止する。

このモジュールの責務:
  1. 利用者証拠フォルダの完全列挙（再帰）
  2. ファイル種別ごとの text 抽出可能性判定
     - PDF: text or scanned-image(OCR 要)
     - EML: text
     - DOCX: text
     - JPG/PNG: vision or OCR
     - MP4: metadata only
  3. SHA256 + size + extracted_chars の記録
  4. coverage % の算出（読了済 / 全件）
  5. 「読了済」フラグ管理（manifest.json）
  6. coverage < threshold なら analyze 拒否（gate)

これは harness.py の L1-L7 と独立に動く前段ゲート。
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("legalshield.evidence_gate")


# ============================================================================
# File Role / Priority Classification (v1.1, added 2026-06-09)
# ============================================================================
# 教訓: v1 で「全ファイル必読」設計したため、forensic raw data まで pending
# 扱いになり、利用者から「raw data は forensic agent 専用」と指摘された。
# 本 LegalShield agent は分析報告のみ読めばよく、raw data は別 agent の責務。

class FileRole:
    REPORT = "report"              # 分析報告 (.md/.pdf) → 必読
    EVIDENCE_DOC = "evidence_doc"  # 契約・mail・内容証明 → 必読
    META = "meta"                  # PORTFOLIO/README/manifest → 優先読
    RAW_DATA = "raw_data"          # ext4 image / raw log → forensic agent 専用
    VISUALIZATION = "visualization"  # 3D 画像 / HTML map → サンプル 1 件で OK
    SCRIPT = "script"              # 分析 .py / .sh → 読不要 (出力 .md を読む)
    UNKNOWN = "unknown"

# パターンによる自動分類（pathlib glob 互換）
ROLE_PATTERNS = {
    FileRole.REPORT: [
        "*REPORT*.md", "*REPORT*.pdf", "*ANALYSIS*.md", "*ANALYSIS*.pdf",
        "*分析*.md", "*分析*.pdf", "*報告*.md", "*報告*.pdf", "*報告書*.pdf",
        "DEEP_ANALYSIS*", "SAFETY_DEFECT*", "FORENSIC*", "BYPASS*",
        "SUPPLEMENTARY*", "LEGAL_ACTION_PLAN*", "ACTION_PLAN*",
        "MASTER_REPORT*", "ADMINISTRATIVE_STRATEGY*", "CRIMINAL_ANALYSIS*",
        "EVIDENCE_INVENTORY*",
    ],
    FileRole.EVIDENCE_DOC: [
        "*契約*.pdf", "*契約*.md", "*内容証明*.pdf", "*内容証明*.docx",
        "*最終要求書*", "*陳述書*", "*通知*.pdf",
        "*.eml", "Order*.pdf", "*Invoice*", "*訂購單*", "甲*号証*",
        "辯護*", "弁護*",
    ],
    FileRole.META: [
        "PORTFOLIO.md", "README.md", "AGENTS.md", "PROGRESS.md",
        "MANIFEST*.txt", "SHA256_CHECKSUMS*.txt", "INDEX.md",
        "manifest.json", "evidence_manifest.json",
    ],
    FileRole.RAW_DATA: [
        "*.img", "*.bin", "*.bag", "*.dat",
        "raw_extracts/*", "full_extraction*/*", "working_data/raw_*",
        "*.kern.log", "*_lines.txt", "boot_markers.txt",
        "syslog*", "*.tlog",
    ],
    FileRole.VISUALIZATION: [
        "*trajectory*.png", "*trajectory*.html", "*map*.html",
        "*timeline*.html", "*visualization*.png", "overlays/*",
    ],
    FileRole.SCRIPT: [
        "*.py", "*.sh", "*.service", "*.yaml", "*.json", "*.cpp", "*.hpp",
        "*.c", "*.h",
    ],
}


def classify_role(relpath: str, size_bytes: int = 0) -> str:
    """Heuristic auto-classification by filename + path patterns."""
    from fnmatch import fnmatch
    p = relpath.replace("\\", "/")
    fname = p.rsplit("/", 1)[-1]
    # raw_data check first (path prefix wins for large generated extracts)
    for role in [FileRole.RAW_DATA, FileRole.VISUALIZATION, FileRole.META,
                 FileRole.REPORT, FileRole.EVIDENCE_DOC, FileRole.SCRIPT]:
        for pat in ROLE_PATTERNS[role]:
            if "/" in pat:
                if fnmatch(p, pat) or fnmatch(p, "**/" + pat):
                    return role
            else:
                if fnmatch(fname, pat):
                    return role
    return FileRole.UNKNOWN


def role_required_for_coverage(role: str) -> bool:
    """Return True if this file MUST be read for the agent to claim coverage."""
    return role in (FileRole.REPORT, FileRole.EVIDENCE_DOC, FileRole.META)


# 構造化的に「テキスト抽出可能か」を判定する
TEXT_NATIVE_EXTS = {".txt", ".md", ".json", ".csv", ".html", ".xml", ".eml"}
PDF_EXTS = {".pdf"}
DOCX_EXTS = {".docx", ".doc"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a"}


@dataclass
class EvidenceFile:
    """1 件の証拠ファイル記録。"""
    relpath: str
    size_bytes: int
    sha256: str
    ext: str
    kind: str            # "text" | "pdf_text" | "pdf_scan" | "docx" | "image" | "video" | "audio" | "unknown"
    extracted_chars: int = 0  # 抽出された文字数（0 ≒ 抽出失敗 or 画像）
    needs_ocr: bool = False
    needs_vision: bool = False
    read_by_agent: bool = False  # agent が中身を確認したか
    read_at: Optional[str] = None
    notes: str = ""
    role: str = "unknown"  # v1.1: FileRole — coverage 計算用 priority

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvidenceManifest:
    """case 単位の証拠 manifest。"""
    case_id: str
    source_dir: str
    files: list[EvidenceFile] = field(default_factory=list)
    indexed_at: Optional[str] = None
    last_audit_at: Optional[str] = None

    @property
    def total(self) -> int:
        return len(self.files)

    @property
    def text_ready(self) -> int:
        """テキスト抽出済みの件数（agent が読める状態）。"""
        return sum(1 for f in self.files if f.extracted_chars > 0)

    @property
    def read_count(self) -> int:
        """agent が実際に読了した件数。"""
        return sum(1 for f in self.files if f.read_by_agent)

    @property
    def required_files(self) -> list:
        """coverage 計算対象（report/evidence_doc/meta のみ）。"""
        return [f for f in self.files if role_required_for_coverage(f.role)]

    @property
    def required_read(self) -> int:
        return sum(1 for f in self.required_files if f.read_by_agent)

    @property
    def required_total(self) -> int:
        return len(self.required_files)

    @property
    def coverage(self) -> float:
        """**重要 (v1.1 訂正)**: required (report+evidence_doc+meta) のみで計算。
        raw_data / script / visualization は別 agent 担当のため対象外。"""
        if self.required_total == 0:
            return 0.0
        return self.required_read / self.required_total

    @property
    def coverage_all_files(self) -> float:
        """全ファイルベースの読了率（参考、coverage の判定には使わない）。"""
        if self.total == 0:
            return 0.0
        return self.read_count / self.total

    @property
    def pending_ocr(self) -> list[EvidenceFile]:
        return [f for f in self.files if f.needs_ocr]

    @property
    def pending_vision(self) -> list[EvidenceFile]:
        return [f for f in self.files if f.needs_vision]

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "source_dir": self.source_dir,
            "indexed_at": self.indexed_at,
            "last_audit_at": self.last_audit_at,
            "total": self.total,
            "text_ready": self.text_ready,
            "read_count": self.read_count,
            "coverage": round(self.coverage, 3),
            "files": [f.to_dict() for f in self.files],
        }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _classify(path: Path) -> tuple[str, bool, bool]:
    """(kind, needs_ocr, needs_vision) を返す。"""
    ext = path.suffix.lower()
    if ext in TEXT_NATIVE_EXTS:
        return ("text", False, False)
    if ext in PDF_EXTS:
        # PDF は text か scan か、抽出してみるまで分からない → 後段で判定
        return ("pdf_unknown", False, False)
    if ext in DOCX_EXTS:
        return ("docx", False, False)
    if ext in IMAGE_EXTS:
        return ("image", True, True)  # 画像は OCR or vision 必要
    if ext in VIDEO_EXTS:
        return ("video", False, True)  # vision で frame 抽出可能
    if ext in AUDIO_EXTS:
        return ("audio", False, False)  # 文字起こし要だが別途
    return ("unknown", False, False)


def index_evidence_folder(case_id: str, source_dir: Path) -> EvidenceManifest:
    """source_dir 配下の全ファイルを列挙し manifest を作る。

    各 PDF は text 抽出を試行し、抽出文字数 < 100 なら needs_ocr=True にする。
    """
    manifest = EvidenceManifest(case_id=case_id, source_dir=str(source_dir))
    files = sorted(source_dir.rglob("*"))
    files = [f for f in files if f.is_file() and ".git" not in str(f)]

    for f in files:
        rel = str(f.relative_to(source_dir))
        kind, needs_ocr, needs_vision = _classify(f)
        role = classify_role(rel, f.stat().st_size)
        ef = EvidenceFile(
            relpath=rel,
            size_bytes=f.stat().st_size,
            sha256=_sha256(f),
            ext=f.suffix.lower(),
            kind=kind,
            needs_ocr=needs_ocr,
            needs_vision=needs_vision,
            role=role,
        )
        # raw_data と script は自動 mark_read（agent 読不要）
        if role in (FileRole.RAW_DATA, FileRole.SCRIPT):
            ef.read_by_agent = True
            ef.notes = f"auto-marked (role={role}, out of scope for LegalShield agent)"
        # PDF の text 抽出テスト
        if kind == "pdf_unknown":
            try:
                import pdfplumber
                with pdfplumber.open(f) as pdf:
                    text_parts = [(p.extract_text() or "") for p in pdf.pages]
                    full_text = "\n".join(text_parts)
                ef.extracted_chars = len(full_text.strip())
                if ef.extracted_chars < 100:
                    ef.kind = "pdf_scan"
                    ef.needs_ocr = True
                    ef.notes = "PDF parse returned <100 chars; likely scanned image PDF"
                else:
                    ef.kind = "pdf_text"
            except Exception as e:
                ef.kind = "pdf_error"
                ef.notes = f"pdfplumber error: {e}"
                ef.needs_ocr = True
        elif kind == "text":
            try:
                ef.extracted_chars = len(f.read_text(encoding="utf-8", errors="replace"))
            except Exception as e:
                ef.notes = f"text read error: {e}"
        elif kind == "docx":
            try:
                from docx import Document
                doc = Document(f)
                text = "\n".join(p.text for p in doc.paragraphs)
                ef.extracted_chars = len(text)
            except Exception as e:
                ef.notes = f"docx error: {e}"

        manifest.files.append(ef)

    manifest.indexed_at = datetime.now(timezone.utc).isoformat()
    return manifest


def save_manifest(manifest: EvidenceManifest, manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_manifest(manifest_path: Path) -> EvidenceManifest:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = [EvidenceFile(**f) for f in data["files"]]
    return EvidenceManifest(
        case_id=data["case_id"],
        source_dir=data["source_dir"],
        files=files,
        indexed_at=data.get("indexed_at"),
        last_audit_at=data.get("last_audit_at"),
    )


def mark_read(manifest: EvidenceManifest, relpath: str, notes: str = "") -> None:
    """agent がそのファイルを読了したことを記録。"""
    for f in manifest.files:
        if f.relpath == relpath:
            f.read_by_agent = True
            f.read_at = datetime.now(timezone.utc).isoformat()
            if notes:
                f.notes = (f.notes + " | " if f.notes else "") + notes
            return
    raise KeyError(f"file {relpath} not in manifest")


# ============================================================================
# Gate: 分析開始前のチェック
# ============================================================================

class EvidenceGateError(RuntimeError):
    """証拠ゲートを通過していないのに分析を開始しようとした。"""


def assert_ready_for_analysis(
    manifest: EvidenceManifest,
    *,
    min_coverage: float = 0.90,
    allow_unindexed: bool = False,
) -> dict:
    """分析開始前に必ず呼ぶ。条件を満たさない場合 EvidenceGateError を上げる。

    Returns:
        diagnostic dict（coverage, blockers）

    Raises:
        EvidenceGateError: gate を通過しなかった
    """
    blockers = []
    if manifest.total == 0 and not allow_unindexed:
        blockers.append("evidence folder empty or not indexed")
    if manifest.coverage < min_coverage:
        blockers.append(
            f"coverage {manifest.coverage:.0%} < required {min_coverage:.0%}"
            f" (read {manifest.read_count}/{manifest.total})"
        )
    # v1.1: only block on required files (raw_data/script/visualization out of scope)
    pending_ocr_req = [f for f in manifest.pending_ocr
                       if not f.read_by_agent and role_required_for_coverage(f.role)]
    if pending_ocr_req:
        blockers.append(
            f"{len(pending_ocr_req)} required files need OCR: "
            + ", ".join(f.relpath for f in pending_ocr_req[:5])
            + (" ..." if len(pending_ocr_req) > 5 else "")
        )
    pending_vision_req = [f for f in manifest.pending_vision
                          if not f.read_by_agent and role_required_for_coverage(f.role)]
    if pending_vision_req:
        blockers.append(
            f"{len(pending_vision_req)} required image/video files not read: "
            + ", ".join(f.relpath for f in pending_vision_req[:5])
            + (" ..." if len(pending_vision_req) > 5 else "")
        )

    diag = {
        "case_id": manifest.case_id,
        "total": manifest.total,
        "read_count": manifest.read_count,
        "coverage": round(manifest.coverage, 3),
        "blockers": blockers,
        "min_coverage": min_coverage,
    }

    if blockers:
        raise EvidenceGateError(
            f"Evidence Gate FAILED for case '{manifest.case_id}': "
            + "; ".join(blockers)
            + "\n→ Read all unread files, run OCR on scanned PDFs, "
            + "and mark_read() each before requesting analysis."
        )

    return diag


def coverage_banner(manifest: EvidenceManifest) -> str:
    """分析報告の先頭に挿入する coverage 透明性 banner。

    v1.1: required (report/evidence_doc/meta) と全体を区別して表示。
    """
    cov = manifest.coverage * 100
    cov_all = manifest.coverage_all_files * 100
    pending_ocr = len([f for f in manifest.pending_ocr
                       if not f.read_by_agent and role_required_for_coverage(f.role)])
    pending_vision = len([f for f in manifest.pending_vision
                          if not f.read_by_agent and role_required_for_coverage(f.role)])
    # role breakdown
    from collections import Counter
    role_breakdown = Counter(f.role for f in manifest.files)
    role_str = ", ".join(f"{k}={v}" for k, v in role_breakdown.most_common())
    return (
        f"\n--- Evidence Coverage (v1.1 priority-aware) ---\n"
        f"Case: {manifest.case_id}\n"
        f"Required read: {manifest.required_read} / {manifest.required_total} ({cov:.1f}%) ★ gate basis\n"
        f"All files read: {manifest.read_count} / {manifest.total} ({cov_all:.1f}%) — reference\n"
        f"Pending OCR (required only): {pending_ocr} files\n"
        f"Pending Vision (required only): {pending_vision} files\n"
        f"Role breakdown: {role_str}\n"
        f"Indexed at: {manifest.indexed_at}\n"
        f"------------------------------------------------\n"
    )
