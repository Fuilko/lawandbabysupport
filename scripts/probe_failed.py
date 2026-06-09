"""Probe whether previously-failed 昭和九年 laws are actually fetchable when polled politely."""
import requests, urllib.parse, time
nums = ['昭和九年勅令第十三号', '昭和九年逓信省令第六号', '昭和九年逓信省・農林省令', '昭和九年大蔵省令第三十五号']
for num in nums:
    r = requests.get(f'https://laws.e-gov.go.jp/api/1/lawdata/{urllib.parse.quote(num)}', timeout=20)
    ct = r.headers.get('Content-Type', '')[:30]
    head = r.text[:60].replace('\n', ' ').replace('\r', ' ')
    is_html = head.lstrip().startswith('<!DOCTYPE')
    print(f'{r.status_code}  ct={ct}  len={len(r.content)}  html={is_html}  | {num}')
    time.sleep(1.0)
