import pandas as pd
from sentence_transformers import SentenceTransformer

uni = pd.read_parquet(r'D:\projects\LegalShield\legalshield\knowledge\unified_knowledge.parquet')
print('existing unified:', len(uni))

df = pd.read_parquet(r'D:\projects\LegalShield\legalshield\knowledge\parsed_facilities.parquet')
print('facilities:', len(df))

model = SentenceTransformer('all-MiniLM-L6-v2')
records = []
for _, row in df.iterrows():
    text = f"{row['category']}施設 {row['name']} {row['address'] or ''} {row['phone'] or ''}"
    records.append({'text': text.strip(), 'source_type': 'facility', 'tags': f'施設,{row["category"]}'})

embs = model.encode([r['text'] for r in records], show_progress_bar=False, convert_to_numpy=True)
for r, v in zip(records, embs):
    r['vector'] = v.tolist()

fac_df = pd.DataFrame(records)
combined = pd.concat([uni, fac_df], ignore_index=True)
combined.to_parquet(r'D:\projects\LegalShield\legalshield\knowledge\unified_knowledge_v2.parquet')
print('combined rows:', len(combined))
