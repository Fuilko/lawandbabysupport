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
    def coverage(self) -> float:
        """読了率（読了 / 全件）。"""
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
        ef = EvidenceFile(
            relpath=rel,
            size_bytes=f.stat().st_size,
            sha256=_sha256(f),
            ext=f.suffix.lower(),
            kind=kind,
            needs_ocr=needs_ocr,
            needs_vision=needs_vision,
        )
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
    pending_ocr = manifest.pending_ocr
    if pending_ocr:
        unread_ocr = [f for f in pending_ocr if not f.read_by_agent]
        if unread_ocr:
            blockers.append(
                f"{len(unread_ocr)} files require OCR but not yet processed: "
                + ", ".join(f.relpath for f in unread_ocr[:5])
                + (" ..." if len(unread_ocr) > 5 else "")
            )
    pending_vision = manifest.pending_vision
    unread_vision = [f for f in pending_vision if not f.read_by_agent]
    if unread_vision:
        blockers.append(
            f"{len(unread_vision)} image/video files not read by agent: "
            + ", ".join(f.relpath for f in unread_vision[:5])
            + (" ..." if len(unread_vision) > 5 else "")
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
    """分析報告の先頭に挿入する coverage 透明性 banner。"""
    cov = manifest.coverage * 100
    pending_ocr = len([f for f in manifest.pending_ocr if not f.read_by_agent])
    pending_vision = len([f for f in manifest.pending_vision if not f.read_by_agent])
    return (
        f"\n--- Evidence Coverage ---\n"
        f"Case: {manifest.case_id}\n"
        f"Read: {manifest.read_count} / {manifest.total} ({cov:.1f}%)\n"
        f"Pending OCR: {pending_ocr} files\n"
        f"Pending Vision: {pending_vision} files\n"
        f"Indexed at: {manifest.indexed_at}\n"
        f"-------------------------\n"
    )
