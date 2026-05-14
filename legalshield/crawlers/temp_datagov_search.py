import requests

# Search data.go.jp for support center datasets
searches = [
    ('児童相談所', 'jidou'),
    ('配偶者暴力', 'dv'),
    ('ワンストップ', 'onestop'),
    ('法テラス', 'houterasu'),
    ('弁護士', 'bengoshi'),
    ('条例', 'jourei'),
]

for keyword, key in searches:
    url = 'https://www.data.go.jp/data/api/action/package_search'
    try:
        r = requests.get(url, params={'q': keyword, 'rows': 5}, timeout=30)
        d = r.json()
        if d.get('success'):
            count = d['result']['count']
            results = d['result']['results']
            print(f"\n=== {keyword} ({count}) ===")
            for pkg in results[:3]:
                org = pkg.get('organization', {})
                print(f"  {pkg['title'][:50]} | {org.get('title', '')}")
    except Exception as e:
        print(f"{keyword} error: {e}")
