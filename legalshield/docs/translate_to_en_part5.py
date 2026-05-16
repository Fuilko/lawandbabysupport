#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final cleanup of all remaining JP text in EN HTML"""

with open('LEGALSHIELD_INTRO_EN.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    # === EMOJI FIX ===
    ('<div class="highlight-title">💡 申請のコツ</div>', '<div class="highlight-title">💡 Application Tips</div>'),
    ('<div class="highlight-title"> Google.org Impact Challenge — 中優先度</div>', '<div class="highlight-title">🔍 Google.org Impact Challenge — Medium Priority</div>'),
    
    # === PAGE 5 TECH STACK TABLE HEADERS ===
    ('<tr><th>層</th><th>技術</th><th>用途</th></tr>', '<tr><th>Layer</th><th>Technology</th><th>Purpose</th></tr>'),
    ('<tr><th>プラットフォーム</th><th>API / パッケージ</th><th>説明</th></tr>', '<tr><th>Platform</th><th>API / Package</th><th>Description</th></tr>'),
    ('<tr><th>プラットフォーム</th><th>API / パッケージ</th><th>コード例</th></tr>', '<tr><th>Platform</th><th>API / Package</th><th>Code Example</th></tr>'),
    ('<tr><th>機能</th><th>iOS Info.plist</th><th>Android Manifest</th></tr>', '<tr><th>Feature</th><th>iOS Info.plist</th><th>Android Manifest</th></tr>'),
    
    # === PAGE 5 TECH DETAILS ===
    ('e Mobile / TensorFlow Lite</td><td>端末内 5重ロール推論</td>', 'e Mobile / TensorFlow Lite</td><td>On-device 5-role inference</td>'),
    ('ceTransformer (all-MiniLM)</td><td>テキストベクトル化</td>', 'ceTransformer (all-MiniLM)</td><td>Text vectorization</td>'),
    ('d><td>FastAPI (Python)</td><td>Auth・統計・専家マッチング</td>', 'd><td>FastAPI (Python)</td><td>Auth, stats, expert matching</td>'),
    ('d>AES-256-GCM + TLS 1.3</td><td>Com信 + 保存暗号化</td>', 'd>AES-256-GCM + TLS 1.3</td><td>Comm + storage encryption</td>'),
    ('td>Figma → Flutter Widgets</td><td>高齢者・標準・専家 3種 UI</td>', 'td>Figma → Flutter Widgets</td><td>3 UI modes: elderly, standard, expert</td>'),
    ('React Native</td><td>iOS + Android クロスプラットフォーム</td></tr>', 'React Native</td><td>iOS + Android cross-platform</td></tr>'),
    ('Tokyo Region</td><td>Domestic dataンター・コンプライアンス</td>', 'Tokyo Region</td><td>Domestic data center, compliance</td>'),
    
    # === PAGE 5 STEPS & DESCRIPTIONS ===
    ('t AI models for on-device execution変換。<br>', 't AI models for on-device execution conversion.<br>'),
    ('法律検索は端末内で完結し、ネットワーク遅延ゼロ。', 'Legal search completes on-device with zero network latency.'),
    ('被害者のスマホは<b>地下室・飛行機モード・電波不安定</b>な場所にいる可能性があります。<br>', 'The victim\'s phone may be in a <b>basement, airplane mode, or unstable signal area</b>.<br>'),
    ('鍵 = ユーザーパスワード + ハードウェアバインド（Secure Enclave / Keystore）<br>', 'Key = user password + hardware binding (Secure Enclave / Keystore)<br>'),
    ('初回ダウンロード時に同期、その後は増分更新のみ（週 ~10-50MB）。<br>', 'Sync at first download, then incremental updates only (~10-50MB/week).<br>'),
    ('サーバーは<b>永遠に復号できません</b>。たとえサーバーが侵害されても、データは無意味です。', 'The server can <b>never decrypt</b>. Even if the server is compromised, the data is meaningless.'),
    
    # === PAGE 6 MOBILE DETAILS ===
    ('• GPS 座標は<b>サーバーに保存せず</b>、端末内の施設検索のみに使用<br>', '• GPS coordinates are <b>NOT stored on server</b>, used only for on-device facility search<br>'),
    ('• SMS 本文テンプレート：<br>', '• SMS body template:<br>'),
    ('• ユーザーはいつでも位置権限を停止可能。権限停止後も他の機能は使用可能', '• Users can revoke location permission anytime. Other features remain usable after revocation'),
    ('• 加害者に被害者が救助を求めていることに気づかれないようにするため<br>', '• To ensure the perpetrator does not notice the victim is calling for help<br>'),
    ('• 文字摘要のみアップロード（「DV・傷害・昨日・夫」等の匿名化キーワード）<br>', '• Only text summaries uploaded (anonymized keywords like "DV, injury, yesterday, husband")<br>'),
    ('• 緊急 SMS は<b>静かに送信</b>、一切の音や振動を発しない<br>', '• Emergency SMS sent <b>silently</b>, no sound or vibration<br>'),
    ('• 緊急時 SMS には<b>都道府県・市区町村レベル</b>のぼかし位置のみ送信<br>', '• Emergency SMS sends only <b>prefecture/municipality-level</b> blurred location<br>'),
    ('• 通話録音は双方の同意が必要（APP 内で同意確認ダイアログを表示）', '• Call recording requires consent from both parties (consent dialog shown in APP)'),
    ('• 録音ファイルは<b>サーバーにアップロードされず</b>、端末内 Whisper モデルで文字起こし後に音声ファイルを', '• Recording files are <b>NOT uploaded to server</b>; on-device Whisper model transcribes, then audio files are '),
    ('削除<br>', 'deleted<br>'),
    
    # === SMS TABLE FIX ===
    ('<tr><td>SMS</td><td>特別な宣言不要（システム SMS App を呼び出す）</td><td>`SEND_SM', '<tr><td>SMS</td><td>No special declaration (calls system SMS app)</td><td>`SEND_SM'),
    
    # === PAGE 2/4 MIXED ===
    ('s, evidence checklists, perpetratorプロファイル、常用狡弁反論マニュアル、AI 対話スクリプトを搭載。</p', 's, evidence checklists, perpetrator profiles, counter-argument manuals, and AI dialogue scripts.</p'),
    
    # === NAV FLAG TEXT (keep as is but these have CJK) ===
    # 日本語, 繁體中文 are language names - acceptable to keep
]

for old_text, new_text in replacements:
    content = content.replace(old_text, new_text)

with open('LEGALSHIELD_INTRO_EN.html', 'w', encoding='utf-8') as f:
    f.write(content)

import re
cjk = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', content)
print(f'Done. Remaining CJK chars: {len(cjk)}')
# Show what's left
matches = re.findall(r'.{0,30}[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF].{0,30}', content)
seen = set()
for m in matches:
    seen.add(m.strip())
for s in sorted(seen)[:20]:
    print(f'  {s}')
