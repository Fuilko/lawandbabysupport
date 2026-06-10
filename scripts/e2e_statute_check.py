"""E2E sanity check: pgvector statute retrieval with real e-LAWS data."""
import sys, time
sys.path.insert(0, r'D:\projects\LegalShield')
from legalshield.backend import pgvector_retrieve as pgr
from sentence_transformers import SentenceTransformer

m = SentenceTransformer('intfloat/multilingual-e5-small')
def embed(t): return m.encode([f'query: {t}'], normalize_embeddings=True)[0].tolist()
sfn = pgr.make_statute_retriever(embed)
pfn = pgr.make_precedent_retriever(embed)

queries = [
    "労働基準法における残業時間の規制",
    "民法 不法行為 損害賠償請求",
    "刑法 詐欺罪 構成要件",
    "消費者契約法 クーリングオフ",
    "DV防止法 保護命令の手続",
    "製造物責任法 欠陥の定義",
]

for q in queries:
    print(f"\n=== {q} ===")
    t0 = time.time()
    srcs = sfn(q, 3)
    print(f"-- statutes ({(time.time()-t0)*1000:.0f}ms) --")
    for s in srcs:
        print(f"  dist={s.score:.4f}  {s.citation}")
        print(f"     {s.text[:100]!r}")
    t0 = time.time()
    srcs = pfn(q, 2)
    print(f"-- precedents ({(time.time()-t0)*1000:.0f}ms) --")
    for s in srcs:
        print(f"  dist={s.score:.4f}  {s.citation}  {s.text[:80]!r}")
