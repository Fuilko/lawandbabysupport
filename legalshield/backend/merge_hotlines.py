import pandas as pd
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
df = pd.read_csv(r'D:\projects\LegalShield\legalshield\knowledge\seeds\national_hotlines.csv', encoding='utf-8-sig')
records = []
for _, row in df.iterrows():
    text = f"{row['category']} {row['name']} {row['phone']} {row['availability']} {row['notes']} {row['prefecture']}"
    records.append({'text': text, 'source_type': 'hotline', 'tags': f"hotline,{row['category']},{row['prefecture']}"})

embs = model.encode([r['text'] for r in records], show_progress_bar=False, convert_to_numpy=True)
for r, v in zip(records, embs):
    r['vector'] = v.tolist()

hot_df = pd.DataFrame(records)
uni = pd.read_parquet(r'D:\projects\LegalShield\legalshield\knowledge\unified_knowledge_v2.parquet')
combined = pd.concat([uni, hot_df], ignore_index=True)
combined.to_parquet(r'D:\projects\LegalShield\legalshield\knowledge\unified_knowledge_v3.parquet')
print('rows:', len(combined))
print('source_types:', combined['source_type'].value_counts().to_dict())
