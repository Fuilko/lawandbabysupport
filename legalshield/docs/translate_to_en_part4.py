#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final supplemental JP→EN translations for EN HTML"""

with open('LEGALSHIELD_INTRO_EN.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    # === FIX BROKEN EMOJI ===
    ('<div class="highlight-title"> Google.org Impact Challenge — 中優先度</div>', '<div class="highlight-title">🔍 Google.org Impact Challenge — Medium Priority</div>'),
    ('<div class="highlight-title"> 💡 申請のコツ</div>', '<div class="highlight-title">💡 Application Tips</div>'),
    
    # === PAGE 5 TECH ARCH REMAINING ===
    ('<div class="section-title">5.2 技術スタック総表</div>', '<div class="section-title">5.2 Tech Stack Overview</div>'),
    ('5重ロール推論は完全に端末内で完結し、<b>録音・写真・位置情報は一切サーバーに送信されません</b>。', '5-role inference completes entirely on-device; <b>recordings, photos, and location data are NEVER sent to servers</b>.'),
    ('<b>LanceDB</b> は組み込み・サーバーレスモードをサポート。<br>', '<b>LanceDB</b> supports embedded/serverless mode.<br>'),
    ('623K 国法ベクトルデータを <b>~500MB</b> に圧縮した端末データベースに。<br>', '623K law vectors compressed to <b>~500MB</b> on-device database.<br>'),
    ('<b>ONNX Runtime Mobile</b> または <b>TensorFlow Lite</b> で AI モデルを端末実行形式に', '<b>ONNX Runtime Mobile</b> or <b>TensorFlow Lite</b> to convert AI models for on-device execution'),
    
    ('<p style="margin-top:14px"><b>Step 2: 端末内 AI 推論（オフライン使用可能）</b></p>', '<p style="margin-top:14px"><b>Step 2: On-Device AI Inference (Offline Capable)</b></p>'),
    ('<p style="margin-top:14px"><b>Step 3: ベクトルデータベースの端末化</b></p>', '<p style="margin-top:14px"><b>Step 3: Device-Embedded Vector Database</b></p>'),
    ('<p style="margin-top:14px"><b>Step 4: 機密データの端末内暗号化</b></p>', '<p style="margin-top:14px"><b>Step 4: On-Device Encryption of Sensitive Data</b></p>'),
    
    ('<tr><td>APP フレームワーク</td><td>Flutter または React Native</td>', '<tr><td>APP Framework</td><td>Flutter or React Native</td>'),
    ('<tr><td>AI 推論</td><td>ONNX Runtime Mobile / TensorFlo', '<tr><td>AI Inference</td><td>ONNX Runtime Mobile / TensorFlo'),
    ('<tr><td>LLM</td><td>Phi-3 / Gemma-2B（量子化）</td><td>小モデル・端末実行・日本語対応</td></tr>', '<tr><td>LLM</td><td>Phi-3 / Gemma-2B (quantized)</td><td>Small model · on-device · Japanese compatible</td></tr>'),
    ('<tr><td>ベクトル DB</td><td>LanceDB（組み込み）</td><td>端末内 RAG 検索</td></tr>', '<tr><td>Vector DB</td><td>LanceDB (embedded)</td><td>On-device RAG search</td></tr>'),
    ('<tr><td>バックエンド API</td><td>FastAPI (Python)</td><td>認証', '<tr><td>Backend API</td><td>FastAPI (Python)</td><td>Auth'),
    ('<tr><td>クラウド</td><td>AWS Tokyo Region</td><td>国内データセ', '<tr><td>Cloud</td><td>AWS Tokyo Region</td><td>Domestic data'),
    ('<tr><td>暗号化</td><td>AES-256-GCM + TLS 1.3</td><td>通', '<tr><td>Encryption</td><td>AES-256-GCM + TLS 1.3</td><td>Com'),
    ('<tr><td>UI 設計</td><td>Figma → Flutter Widgets</td><td', '<tr><td>UI Design</td><td>Figma → Flutter Widgets</td><td'),
    
    ('<tr><td><b>PWA (Web APP)</b></td><td>最速リリース、審査不要、Web 即 APP</td><td>ネイティブ機能制限あり', '<tr><td><b>PWA (Web APP)</b></td><td>Fastest release, no review, web-to-app instantly</td><td>Native feature limitations'),
    ('<td>ブラウザサンドボックスの制限あり。Web MVP 向け。本番はネイティブ APP を推奨</td>', '<td>Browser sandbox limitations. For web MVP. Native APP recommended for production.</td>'),
    ('<td>⭐⭐⭐⭐<br>MVP 最適</td></tr>', '<td>⭐⭐⭐⭐<br>Best for MVP</td></tr>'),
    
    # === PAGE 6 MOBILE REMAINING ===
    ('<!-- PAGE 6: スマホ機能 -->', '<!-- PAGE 6: Mobile Features -->'),
    ('<div class="tagline">スマホ機能連携ガイド</div>', '<div class="tagline">Mobile Integration Guide</div>'),
    ('<div class="section-title">6. スマホのネイティブ機能を呼び出すには？</div>', '<div class="section-title">6. How to Call Smartphone Native Features?</div>'),
    ('<p>LegalShield は GPS・カメラ・マイク・SMS 等のスマホ機能を利用します。各機能の実装方法は以下の通りです。</p>', '<p>LegalShield uses GPS, camera, microphone, SMS, and other smartphone features. Implementation methods are as follows.</p>'),
    
    ('<div class="section-title">6.1 GPS 位置情報</div>', '<div class="section-title">6.1 GPS Location</div>'),
    ('<p><b>用途</b>：最寄り支援機関検索・緊急時位置送信・証拠 GPS タグ付け</p>', '<p><b>Use:</b> nearest support search, emergency location send, evidence GPS tagging</p>'),
    
    ('<div class="section-title">6.2 カメラ（証拠撮影）</div>', '<div class="section-title">6.2 Camera (Evidence Photography)</div>'),
    ('<p><b>用途</b>：傷害写真・事故現場・器物損壊・LINE スクリーンショット保存</p>', '<p><b>Use:</b> injury photos, accident scenes, property damage, LINE screenshot preservation</p>'),
    ('<td>撮影後に自動で<b>タイムスタンプ + GPS 座標 + SHA-256 ハッシュ値</b>の透かしを付加</td>', '<td>Auto-embed <b>timestamp + GPS coordinates + SHA-256 hash</b> watermark after capture</td>'),
    
    ('<div class="section-title">6.3 マイク（録音・音声入力）</div>', '<div class="section-title">6.3 Microphone (Recording & Voice Input)</div>'),
    ('<p><b>用途</b>：事件陳述録音・通話録音（同意の下）・AI 音声対話</p>', '<p><b>Use:</b> incident statement recording, call recording (with consent), AI voice dialogue</p>'),
    ('<td>録音と同時にリアルタイム文字起こし、AI が自動でキーワード抽出</td>', '<td>Real-time transcription during recording, AI auto keyword extraction</td>'),
    ('<td>Google Speech-to-Text 連携、日本語高精度</td>', '<td>Google Speech-to-Text integration, high-accuracy Japanese</td>'),
    
    ('<div class="section-title">6.4 SMS ショートメール（緊急通知）</div>', '<div class="section-title">6.4 SMS Short Message (Emergency Alert)</div>'),
    ('<p><b>用途</b>：10秒カウントダウン後の信頼連絡先・支援機関への自動送信</p>', '<p><b>Use:</b> auto-send to trusted contacts and support agencies after 10-sec countdown</p>'),
    ('<i>「【自動送信】○○（名前）が緊急事態に遭遇しました。<br>位置：東京都○○区（GPS 座標は送信されません）<br>時刻：2026/05/14 14:32<br>このメッセージは自動生成されたものです。」</i>', '<i>"[AUTO-SEND] ○○ (name) has encountered an emergency.<br>Location: Tokyo ○○ Ward (GPS coordinates not sent)<br>Time: 2026/05/14 14:32<br>This message was auto-generated."</i>'),
    ('<td>同上、システム SMS を呼び出して送信</td>', '<td>Same as above, calls system SMS to send</td>'),
    
    ('<div class="section-title">6.5 権限申請一覧（iOS / Android）</div>', '<div class="section-title">6.5 Permission Request List (iOS / Android)</div>'),
    ('<tr><th>機能</th><th>iOS Info.plist</th><th>Android Manifest</th></tr>', '<tr><th>Feature</th><th>iOS Info.plist</th><th>Android Manifest</th></tr>'),
    ('<tr><td>GPS / 位置情報</td><td>', '<tr><td>GPS / Location</td><td>'),
    ('<tr><td>カメラ</td><td>`NSCameraUsageDescription`</td>', '<tr><td>Camera</td><td>`NSCameraUsageDescription`</td>'),
    ('<tr><td>マイク</td><td>`NSMicrophoneUsageDescription`</td>', '<tr><td>Microphone</td><td>`NSMicrophoneUsageDescription`</td>'),
    ('<tr><td>SMS</td><td>', '<tr><td>SMS</td><td>'),
    ('<tr><td>通知</td><td>`UNUserNotificationCenter`</td>', '<tr><td>Notifications</td><td>`UNUserNotificationCenter`</td>'),
    ('<tr><td>生体認証</td><td>`NSFaceIDUsageDescription`</td>', '<tr><td>Biometrics</td><td>`NSFaceIDUsageDescription`</td>'),
    
    ('<div class="highlight-title">📱 無音モード（Silent Mode）</div>', '<div class="highlight-title">📱 Silent Mode</div>'),
    ('<div class="highlight-title">🔒 録音プライバシー設計</div>', '<div class="highlight-title">🔒 Recording Privacy Design</div>'),
    ('<div class="highlight-title">⚠️ プライバシー保護原則</div>', '<div class="highlight-title">⚠️ Privacy Protection Principles</div>'),
    
    # Page 5 remaining
    ('<div class="section-title">5. システムアーキテクチャ概要</div>', '<div class="section-title">5. System Architecture Overview</div>'),
    
    # Page 1 intro remaining
    ('<p>LegalShield は日本で最も多い <b>17類型</b>の犯罪と権利侵害に対応。各タイプには黄金時間、証拠チェックリスト、加害者', '<p>LegalShield covers the <b>17 most common</b> crime and rights violation types in Japan. Each type includes golden hours, evidence checklists, perpetrator'),
    
    # Fix any remaining in tables
    ('<tr><th>プラットフォーム</th><th>API / パッケージ</th><th>コード例</th></tr>', '<tr><th>Platform</th><th>API / Package</th><th>Code Example</th></tr>'),
]

for old_text, new_text in replacements:
    content = content.replace(old_text, new_text)

with open('LEGALSHIELD_INTRO_EN.html', 'w', encoding='utf-8') as f:
    f.write(content)

import re
cjk = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', content)
print(f'Done. Remaining CJK chars: {len(cjk)}')
