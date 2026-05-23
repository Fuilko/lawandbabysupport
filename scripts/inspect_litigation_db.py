"""Inspect the litigation.duckdb to see what we collected."""
import sys
import io
import duckdb

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

con = duckdb.connect("legalshield/lancedb/litigation.duckdb")
print("=== Tables ===")
for r in con.execute("SHOW TABLES").fetchall():
    print(" ", r[0])
print()

print("=== CALL4 summary ===")
n = con.execute("SELECT COUNT(*) FROM call4_cases").fetchone()[0]
print(f"Total cases: {n}")
total_bytes = con.execute("SELECT SUM(LENGTH(full_text)) FROM call4_cases").fetchone()[0]
print(f"Total full_text chars: {total_bytes:,}")
print()

print("=== Sample 8 cases ===")
sql = """
SELECT case_id, title_ja, court, plaintiff_count, LENGTH(full_text) AS tlen
FROM call4_cases ORDER BY case_id LIMIT 8
"""
for row in con.execute(sql).fetchall():
    case_id, title, court, pc, tlen = row
    print(f"  {case_id} | {(title or '')[:60]:60s} | court={(court or '')[:30]:30s} | plaintiffs={pc} | text_len={tlen}")
print()

print("=== Cases with non-null court field ===")
n = con.execute("SELECT COUNT(*) FROM call4_cases WHERE court IS NOT NULL AND court <> ''").fetchone()[0]
print(f"  {n} / {con.execute('SELECT COUNT(*) FROM call4_cases').fetchone()[0]}")

print()
print("=== Court forms (if collected) ===")
try:
    n = con.execute("SELECT COUNT(*) FROM court_forms").fetchone()[0]
    print(f"Total forms: {n}")
    by_cat = con.execute(
        "SELECT category, COUNT(*) FROM court_forms GROUP BY category ORDER BY 2 DESC"
    ).fetchall()
    for cat, c in by_cat:
        print(f"  · {cat}: {c}")
except Exception as e:
    print(f"  table not ready yet: {e}")
