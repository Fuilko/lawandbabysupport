#!/usr/bin/env python3
"""
在丟給雲端 AI（特別是中國 AI 如 Kimi/DeepSeek）之前，自動去識別化敏感內容。

使用方式:
  # 從檔案輸入
  python3 sanitize_before_ai.py < input.txt > sanitized.txt
  
  # 從剪貼簿（Mac）
  pbpaste | python3 sanitize_before_ai.py | pbcopy
  
  # 互動模式
  python3 sanitize_before_ai.py
  （貼上內容後按 Ctrl+D）
"""

import re
import sys

# 敏感詞替換對照表
# 順序很重要：較具體的規則放前面
REPLACEMENTS = [
    # ──── 機構名（日本） ────
    (r"豐田財団|豊田財団|Toyota Foundation|トヨタ財団", "某基金會"),
    (r"児童相談所|兒童相談所", "某行政單位"),
    (r"配偶者暴力相談支援センター", "某支援中心"),
    (r"労働基準監督署|労基署", "某勞動監督單位"),
    (r"消費生活センター", "某消費者中心"),
    (r"東京都新宿区[^\s]*", "某都會區"),
    (r"東京都[^\s]*区", "某都會區"),
    (r"東京逓信病院|東京医師会", "某醫療機構"),
    
    # ──── 個人/開發者 ────
    (r"Fuilko|fuiko|フイコ", "[開發者]"),
    
    # ──── 網路/伺服器 ────
    (r"100\.76\.\d+\.\d+", "[本地伺服器]"),
    (r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", "[IP]"),
    (r"https?://[^\s/]+\.(?:com|net|org|jp|tw|cn|io)[^\s]*", "[URL]"),
    
    # ──── API Keys（依優先順序） ────
    (r"sk-[a-zA-Z0-9]{20,}", "[OPENAI_KEY]"),
    (r"sk-ant-[a-zA-Z0-9-]{20,}", "[ANTHROPIC_KEY]"),
    (r"ghp_[a-zA-Z0-9]{30,}", "[GITHUB_TOKEN]"),
    (r"github_pat_[a-zA-Z0-9_]{30,}", "[GITHUB_TOKEN]"),
    (r"hf_[a-zA-Z0-9]{30,}", "[HF_TOKEN]"),
    (r"AKIA[A-Z0-9]{16}", "[AWS_KEY]"),
    (r"AIza[a-zA-Z0-9_-]{30,}", "[GOOGLE_KEY]"),
    (r"xox[baprs]-[a-zA-Z0-9-]{10,}", "[SLACK_TOKEN]"),
    
    # ──── 個人聯繫資訊 ────
    (r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", "[EMAIL]"),
    (r"0\d{1,4}-\d{1,4}-\d{4}", "[JP_PHONE]"),       # 日本電話
    (r"\+81[-\s]?\d{1,4}[-\s]?\d{1,4}[-\s]?\d{4}", "[JP_PHONE]"),
    (r"\b09\d{2}-\d{4}-\d{4}\b", "[JP_MOBILE]"),    # 日本手機
    (r"\b\d{3}-\d{4}\b", "[JP_POSTAL]"),            # 日本郵遞區號
    
    # ──── 身分證號 ────
    (r"[A-Z]\d{9}", "[TW_ID]"),                     # 台灣身分證
    (r"\d{6}-\d{4}-\d{4}-\d{4}", "[JP_MYNUMBER]"), # 日本個人番號
    
    # ──── 金額（保留量級） ────
    (r"\d{4,}萬円|\d{4,}万円|\d{4,}萬日圓", "數千萬日圓"),
    (r"\d{3}萬円|\d{3}万円|\d{3}萬日圓", "數百萬日圓"),
    (r"\d{4,}萬|\d{4,}万", "數千萬"),
    
    # ──── GPS 座標 ────
    (r"\b3[5-7]\.\d{4,}\s*,\s*1[3-4]\d\.\d{4,}\b", "[GPS_JP]"),
    
    # ──── SHA-256 hash（保留前後 4 字以供辨識） ────
    (r"\b[a-f0-9]{64}\b", lambda m: m.group()[:4] + "..." + m.group()[-4:]),
]


def sanitize(text: str) -> tuple[str, dict]:
    """
    去識別化文字內容
    
    Returns:
        (sanitized_text, replacement_stats)
    """
    stats = {}
    
    for pattern, replacement in REPLACEMENTS:
        if callable(replacement):
            matches = re.findall(pattern, text)
            text = re.sub(pattern, replacement, text)
            if matches:
                stats[f"hash_truncated"] = stats.get("hash_truncated", 0) + len(matches)
        else:
            matches = re.findall(pattern, text)
            if matches:
                text = re.sub(pattern, replacement, text)
                key = replacement.strip("[]")
                stats[key] = stats.get(key, 0) + len(matches)
    
    return text, stats


def main():
    # 讀取輸入
    if sys.stdin.isatty():
        print("📋 請貼上要去識別化的內容，完成後按 Ctrl+D：", file=sys.stderr)
    
    input_text = sys.stdin.read()
    
    if not input_text.strip():
        print("⚠️  輸入為空", file=sys.stderr)
        sys.exit(1)
    
    sanitized, stats = sanitize(input_text)
    
    # 輸出到 stdout（可以接 | pbcopy）
    print(sanitized)
    
    # 統計輸出到 stderr（不影響 pipe）
    if stats:
        print("\n" + "=" * 50, file=sys.stderr)
        print("🔒 已替換的敏感資訊：", file=sys.stderr)
        for key, count in sorted(stats.items()):
            print(f"  • {key}: {count} 處", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        print("✅ 現在可以安全地貼給 Kimi/DeepSeek/GPT 了", file=sys.stderr)
    else:
        print("\n✅ 沒有偵測到敏感資訊（但仍建議人工審查）", file=sys.stderr)


if __name__ == "__main__":
    main()
