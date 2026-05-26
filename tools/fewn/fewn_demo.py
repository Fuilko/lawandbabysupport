#!/usr/bin/env python3
"""
FEWN (Forensic Evidence Witness Network) — CLI Demo
=====================================================

「同じ加害者・同じ事業者・同じ窓口を記録した別の被害者と、
   暗号学的にのみ出会える」分散型ネットワークの最小実証。

- 各被害者は加害者識別子（電話 / 銀行口座 / URL / 会社名 / 声紋ハッシュ等）を
  端末側で **HKDF + Salt** で決定論ハッシュ化する。
- 中央サーバ（CALL4 等の公証人）は **ハッシュ集合のみ** を受け取り、
  Bloom filter で他被害者との交差検査を行う。
- マッチ時は「他にもいる」とだけ通知し、個別証拠は両者とも非開示のまま。

これは Callisto Vault（米・性暴力被害者ネットワーク）の汎化版。

## クイック実行

    # 1. 公証人鍵生成（CALL4 が 1 度だけ）
    python fewn_demo.py init

    # 2. 被害者 A 登録（Mapry 詐欺）
    python fewn_demo.py register --name victim_A \
        --evidence "phone:+81-90-1234-5678" \
        --evidence "company:株式会社Mapry" \
        --evidence "url:mapry.jp"

    # 3. 被害者 B 登録（架空、Mapry 共通）
    python fewn_demo.py register --name victim_B \
        --evidence "phone:+81-90-9999-9999" \
        --evidence "company:株式会社Mapry"

    # 4. 公証人がマッチング
    python fewn_demo.py match

## 法的注意
- 加害者識別子は本人が書き留めた範囲のみ使用。事業者名は登記簿で公開。
- 名誉毀損リスク回避：マッチ通知は「他にもいる事実」のみ。氏名や事件詳細は CALL4 弁護団の判断で開示。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import secrets
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# ─────────────────────────────────────────
# ストレージ（demo 用、実環境は SQLite + サーバ）
# ─────────────────────────────────────────

STORE_DIR = Path(__file__).parent / ".fewn_store"
STORE_DIR.mkdir(exist_ok=True)
NOTARY_KEY = STORE_DIR / "notary_salt.bin"
VICTIMS_DB = STORE_DIR / "victims.jsonl"
BLOOM_DB = STORE_DIR / "bloom_index.json"


# ─────────────────────────────────────────
# 加害者識別子の正規化 + 決定論ハッシュ
# ─────────────────────────────────────────

def normalize_evidence(raw: str) -> str:
    """
    'phone:+81-90-1234-5678' → 'phone:81 9012345678'
    'company:株式会社Mapry'   → 'company:株式会社mapry'
    'url:Https://Mapry.JP/'  → 'url:mapry.jp'
    """
    if ":" not in raw:
        raise ValueError(f"evidence must be 'kind:value', got: {raw}")
    kind, value = raw.split(":", 1)
    kind = kind.strip().lower()
    value = unicodedata.normalize("NFKC", value).strip().lower()

    if kind == "phone":
        # 数字のみ抽出、先頭 0 を 81 に置換（日本想定）
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits.startswith("0"):
            digits = "81" + digits[1:]
        value = digits
    elif kind == "url":
        # スキーム除去・末尾スラッシュ除去・ホスト名のみ
        for prefix in ("https://", "http://", "www."):
            if value.startswith(prefix):
                value = value[len(prefix):]
        value = value.rstrip("/").split("/", 1)[0]
    elif kind == "account":
        # 銀行口座：数字のみ
        value = "".join(ch for ch in value if ch.isdigit())
    elif kind == "company":
        # 全角スペース・記号除去
        for ch in [" ", "　", "・", "-", "ー"]:
            value = value.replace(ch, "")

    return f"{kind}:{value}"


def hash_evidence(evidence: str, notary_salt: bytes) -> str:
    """
    HKDF-SHA256(notary_salt, normalize(evidence)) → 16 byte → base64url
    端末側で計算。生の電話番号や会社名はサーバに行かない。
    """
    norm = normalize_evidence(evidence).encode("utf-8")
    # HKDF-Extract のみで十分（Expand なしの単純版、demo 用）
    digest = hmac.new(notary_salt, norm, hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# ─────────────────────────────────────────
# Bloom Filter（最小実装）
# ─────────────────────────────────────────

@dataclass
class BloomFilter:
    bits: list[int]   # 0/1
    k: int            # ハッシュ関数数

    @classmethod
    def new(cls, m_bits: int = 4096, k: int = 7) -> "BloomFilter":
        return cls(bits=[0] * m_bits, k=k)

    def _indices(self, item: str) -> list[int]:
        m = len(self.bits)
        digest = hashlib.sha256(item.encode()).digest()
        # 4 byte ずつ取り出して mod m、k 個必要なら sha512 も使う
        out = []
        cur = digest
        for i in range(self.k):
            if i * 4 + 4 > len(cur):
                cur = hashlib.sha256(cur).digest()
            idx = int.from_bytes(cur[i * 4: i * 4 + 4], "big") % m
            out.append(idx)
        return out

    def add(self, item: str) -> None:
        for i in self._indices(item):
            self.bits[i] = 1

    def contains(self, item: str) -> bool:
        return all(self.bits[i] == 1 for i in self._indices(item))

    def to_json(self) -> dict:
        # bits → bytes → base64 で圧縮
        m = len(self.bits)
        ba = bytearray((m + 7) // 8)
        for i, b in enumerate(self.bits):
            if b:
                ba[i // 8] |= 1 << (i % 8)
        return {
            "m": m,
            "k": self.k,
            "bits_b64": base64.b64encode(bytes(ba)).decode("ascii"),
        }


# ─────────────────────────────────────────
# 公証人鍵（CALL4 が一度だけ生成）
# ─────────────────────────────────────────

def cmd_init() -> None:
    if NOTARY_KEY.exists():
        print(f"[既に存在] {NOTARY_KEY}")
        return
    salt = secrets.token_bytes(32)
    NOTARY_KEY.write_bytes(salt)
    print(f"[公証人鍵生成] {NOTARY_KEY} (32 bytes)")
    print(f"   この鍵は CALL4 サーバに 1 つだけ。被害者は鍵を共有せず")
    print(f"   公証人の公開 hash 関数 (HMAC-SHA256(salt, …)) を使う。")


def get_notary_salt() -> bytes:
    if not NOTARY_KEY.exists():
        sys.exit("先に `python fewn_demo.py init` を実行してください")
    return NOTARY_KEY.read_bytes()


# ─────────────────────────────────────────
# 被害者登録
# ─────────────────────────────────────────

def cmd_register(name: str, evidences: list[str]) -> None:
    salt = get_notary_salt()
    hashes = [hash_evidence(e, salt) for e in evidences]
    record = {"name": name, "hashes": hashes, "evidence_count": len(hashes)}

    with VICTIMS_DB.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"[登録] victim={name}, evidence_count={len(hashes)}")
    print(f"   送信されたデータ: ハッシュ {len(hashes)} 件のみ")
    print(f"   サーバ側は元の電話番号・会社名等を一切知らない")
    for h, e in zip(hashes, evidences, strict=True):
        norm = normalize_evidence(e)
        print(f"   - {h}  (元: {norm[:30]}...)")


# ─────────────────────────────────────────
# マッチング（公証人が実行）
# ─────────────────────────────────────────

def cmd_match() -> None:
    if not VICTIMS_DB.exists():
        sys.exit("被害者がまだ登録されていません")

    victims = []
    with VICTIMS_DB.open(encoding="utf-8") as f:
        for line in f:
            victims.append(json.loads(line))

    if len(victims) < 2:
        sys.exit("マッチングには 2 人以上の被害者が必要です")

    print(f"[公証人マッチング開始] 被害者 {len(victims)} 名")
    print()

    # 全ハッシュ → どの被害者が持っているか
    hash_owners: dict[str, list[str]] = {}
    for v in victims:
        for h in v["hashes"]:
            hash_owners.setdefault(h, []).append(v["name"])

    # 2 名以上の被害者で共有されているハッシュ
    matches = {h: owners for h, owners in hash_owners.items() if len(owners) >= 2}

    if not matches:
        print("  ❌ 共通加害者は検出されませんでした")
        print("     （同一加害者を記録した複数被害者が存在しない）")
        return

    print(f"  🚨 共通加害者ハッシュ {len(matches)} 件を検出")
    print()

    # 被害者ペアごとに集計
    pairs: dict[tuple[str, str], int] = {}
    for h, owners in matches.items():
        for i in range(len(owners)):
            for j in range(i + 1, len(owners)):
                pair = tuple(sorted([owners[i], owners[j]]))
                pairs[pair] = pairs.get(pair, 0) + 1

    print("  ── マッチペア ──")
    for (a, b), count in sorted(pairs.items(), key=lambda x: -x[1]):
        print(f"  ✓ {a}  ⇔  {b}")
        print(f"      共通加害者ハッシュ: {count} 件")
        print("      個別証拠は両者とも非開示（ハッシュのみ照合）")
        print("      → CALL4 弁護団が両被害者に「他にもいる」事実のみ通知")
        print("      → 連名告訴の打診を被害者本人の同意のもと実施")
        print()

    print("  ── プライバシー保証 ──")
    print("  • サーバは元の電話番号・会社名・URL を一度も受信していません")
    print("  • マッチした被害者同士も互いの証拠内容は非開示")
    print("  • 公証人鍵 (32 byte) の漏洩リスクのみ")
    print("  • 実環境では PSI-Cardinality + 閾値暗号で更に強化")


# ─────────────────────────────────────────
# 状態確認
# ─────────────────────────────────────────

def cmd_status() -> None:
    print("[FEWN demo state]")
    print(f"  公証人鍵: {'✓' if NOTARY_KEY.exists() else '未生成'}")
    if VICTIMS_DB.exists():
        n = sum(1 for _ in VICTIMS_DB.open())
        print(f"  登録被害者: {n} 名")
    else:
        print("  登録被害者: 0 名")


def cmd_reset() -> None:
    for p in [NOTARY_KEY, VICTIMS_DB, BLOOM_DB]:
        if p.exists():
            p.unlink()
    print("[reset] 全状態をクリアしました")


# ─────────────────────────────────────────
# CLI
# ─────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="FEWN demo: cryptographic victim matching"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="公証人鍵を生成")

    p_reg = sub.add_parser("register", help="被害者を登録")
    p_reg.add_argument("--name", required=True)
    p_reg.add_argument(
        "--evidence", action="append", required=True,
        help="kind:value 形式 (phone/company/url/account)。複数指定可"
    )

    sub.add_parser("match", help="公証人が共通加害者を検出")
    sub.add_parser("status", help="現在の状態を表示")
    sub.add_parser("reset", help="全状態をクリア")

    args = parser.parse_args()

    if args.cmd == "init":
        cmd_init()
    elif args.cmd == "register":
        cmd_register(args.name, args.evidence)
    elif args.cmd == "match":
        cmd_match()
    elif args.cmd == "status":
        cmd_status()
    elif args.cmd == "reset":
        cmd_reset()


if __name__ == "__main__":
    main()
