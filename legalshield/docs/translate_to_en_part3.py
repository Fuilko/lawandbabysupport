#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Complete remaining JP→EN translations for EN HTML (Page 2, 4 portals, 5, 6)"""

with open('LEGALSHIELD_INTRO_EN.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    # === TITLE & META ===
    ('<title>LegalShield — プロジェクト紹介・機能説明・申請ガイド</title>', '<title>LegalShield — Project Introduction, Features & Application Guide</title>'),
    
    # === PAGE 2 ===
    ('<!-- PAGE 2: 機能 -->', '<!-- PAGE 2: Features -->'),
    ('<div class="tagline">機能紹介</div>', '<div class="tagline">Feature Overview</div>'),
    ('<div class="section-title">2. AI 5重ロールシステム</div>', '<div class="section-title">2. AI 5-Role System</div>'),
    ('<p>LegalShield の AI は <b>5つの専門家ロール</b>を同時に果たし、事件発生から専家マッチングまで全程をサポートします。</p>', '<p>LegalShield\'s AI simultaneously performs <b>5 expert roles</b>, supporting victims from incident occurrence through expert matching.</p>'),
    ('<tr><th>ロール</th><th>機能</th><th>被害者が得られる助け</th></tr>', '<tr><th>Role</th><th>Function</th><th>Help for Victims</th></tr>'),
    ('<td><b>🚨 緊急対応官</b></td>', '<td><b>🚨 Emergency Responder</b></td>'),
    ('<td>ワンタッチで 110 / #8898 / #7119 通報・GPS 位置共有・無音モード・10秒カウントダウン自動通知</td>', '<td>One-touch dial 110 / #8898 / #7119, GPS sharing, silent mode, 10-sec countdown auto-alert</td>'),
    ('<td>命の危機時、考えなくても押せばいい</td>', '<td>In life-threatening moments, just press — no thinking required</td>'),
    ('<td><b>📁 証拠保全官</b></td>', '<td><b>📁 Evidence Collector</b></td>'),
    ('<td>写真・録音・書類の自動整理、SHA-256 ハッシュ・タイムスタンプ・GPS タグ付け・AES-256 暗号化・保全証明書自動生成</td>', '<td>Auto-organize photos, recordings, documents. SHA-256 hash, timestamp, GPS tag, AES-256 encryption, auto preservation certificate</td>'),
    ('<td>証拠が失われない、改竄されない、裁判所提出可能</td>', '<td>Evidence never lost, never tampered, court-admissible</td>'),
    ('<td><b>⚖️ 法律分析師</b></td>', '<td><b>⚖️ Legal Analyst</b></td>'),
    ('<td>623K 国法 + 724K 判例の RAG 検索・関連法条即時提示・適用罪名自動判定</td>', '<td>RAG search 623K laws + 724K precedents, instant relevant article suggestion, auto crime classification</td>'),
    ('<td>「私が今遭遇していることは、法律では何と呼ばれるの？」</td>', '<td>"What is my situation called in law?"</td>'),
    ('<td><b>🧭 戦略模擬師</b></td>', '<td><b>🧭 Strategy Simulator</b></td>'),
    ('<td>刑事告訴・民事訴訟・ADR 調停・行政申訴・保護命令申請——5つのパスの時間・費用・成功率比較</td>', '<td>Criminal complaint, civil suit, ADR mediation, administrative appeal, protection order — compare 5 paths by time, cost, success rate</td>'),
    ('<td>「今の私の状況に最適な道はどれ？」</td>', '<td>"Which path is best for my current situation?"</td>'),
    ('<td><b>🗺️ 専家紹介ナビゲーター</b></td>', '<td><b>🗺️ Expert Referral Navigator</b></td>'),
    ('<td>GPS 連動で最寄りの支援機関（弁護士会・NPO・法テラス・シェルター）をマッチング・予約スクリプト・準備書類チェック・費用減免確認</td>', '<td>GPS-linked matching to nearest support (bar associations, NPOs, legal aid, shelters), booking scripts, document checklist, fee waiver verification</td>'),
    ('<td>「私の近くに、誰が助けてくれる人がいるの？」</td>', '<td>"Who near me can help?"</td>'),
    
    ('<div class="section-title">17類型犯罪対応一覧</div>', '<div class="section-title">17 Crime Types Covered</div>'),
    ('<p>LegalShield は日本で最も多い <b>17類型</b>の犯罪と権利侵害に対応。各タイプには黄金時間、証拠チェックリスト、加害者プロファイル、常用狡弁反論マニュアル、AI 対話スクリプトが内蔵されています。</p>', '<p>LegalShield covers the <b>17 most common</b> crime and rights violation types in Japan. Each type includes golden hours, evidence checklists, perpetrator profiles, counter-argument manuals, and AI dialogue scripts.</p>'),
    ('<tr><th>#</th><th>タイプ</th><th>法的根拠</th><th>黄金時間</th><th>AI 対話スクリプト</th></tr>', '<tr><th>#</th><th>Type</th><th>Legal Basis</th><th>Golden Hours</th><th>AI Dialogue Script</th></tr>'),
    
    # === PAGE 3 TIMELINE MIXED ===
    ('<tr><td>2026年2月</td><td>Developer personally experienced a drone accident in Taiwan, discovered 34 safety defects. Began researching Japan\'s legal and victim support systems.</td></tr>', '<tr><td>Feb 2026</td><td>Developer personally experienced a drone accident in Taiwan, discovered 34 safety defects. Began researching Japan\'s legal and victim support systems.</td></tr>'),
    ('<tr><td>2026年3月</td><td>LegalShield concept: AI × Victim Support × Anti-Grafting. Combined personal litigation/ADR preparation experience with mass evidence management expertise.</td></tr>', '<tr><td>Mar 2026</td><td>LegalShield concept: AI × Victim Support × Anti-Grafting. Combined personal litigation/ADR preparation experience with mass evidence management expertise.</td></tr>'),
    ('<tr><td>2026年4月</td><td>Started crawling national laws (e-LAWS XML 623K items), precedents, and statistics. Leveraged Kochi University research database access.</td></tr>', '<tr><td>Apr 2026</td><td>Started crawling national laws (e-LAWS XML 623K items), precedents, and statistics. Leveraged Kochi University research database access.</td></tr>'),
    ('<tr><td>2026年5月上旬</td><td>Completed vector database (LanceDB), RAG search system, and AI 5-role prototype.</td></tr>', '<tr><td>Early May 2026</td><td>Completed vector database (LanceDB), RAG search system, and AI 5-role prototype.</td></tr>'),
    ('<tr><td>2026年5月中旬</td><td>Completed emergency mode design, anti-grafting feature, 17-type crime taxonomy (criminal law focus), and perpetrator profile database.</td></tr>', '<tr><td>Mid-May 2026</td><td>Completed emergency mode design, anti-grafting feature, 17-type crime taxonomy (criminal law focus), and perpetrator profile database.</td></tr>'),
    ('<tr><td>2026年5月下旬</td><td>(Planned) Grant applications, partnership development, TEAMS 5 tech collaboration, and pilot operations.</td></tr>', '<tr><td>Late May 2026</td><td>(Planned) Grant applications, partnership development, TEAMS 5 tech collaboration, and pilot operations.</td></tr>'),
    ('<tr><td>2026年後半</td><td>(Planned) Expansion into civil/administrative law, deeper precedent research, PhD enrollment, and academic collaboration.</td></tr>', '<tr><td>H2 2026</td><td>(Planned) Expansion into civil/administrative law, deeper precedent research, PhD enrollment, and academic collaboration.</td></tr>'),
    
    # 拡張計画 mixed
    ('<li><b>民法上のBreach of Sales Contract</b> — Debt default and warranty liability</li>', '<li><b>Breach of Sales Contract (Civil Law)</b> — Debt default and warranty liability</li>'),
    ('<li><b>行政法</b> — Administrative Appeals・国家賠償・情報公開請求</li>', '<li><b>Administrative Law</b> — Administrative Appeals, State Compensation, Information Disclosure Requests</li>'),
    
    # === PAGE 4 PORTALS ===
    ('<b>Application Portal:</b>ウェブ申請書（オンライン）／年1-2回募集（通常3月・9月頃）<br>', '<b>Application Portal:</b>Web application (online) / 1-2 rounds per year (usually Mar & Sep)<br>'),
    ('<b>Contact:</b>03-5405-6070（平日9:30-17:30）<br>', '<b>Contact:</b>03-5405-6070 (Weekdays 9:30-17:30)<br>'),
    ('<b>Application Portal:</b>ウェブ申請書／年1回募集（通常4月-5月）<br>', '<b>Application Portal:</b>Web application / 1 round per year (usually Apr-May)<br>'),
    ('<b>Application Portal:</b>担当者窓口（事前問い合わせ必須）／随時受付<br>', '<b>Application Portal:</b>Contact officer (inquiry required) / Ongoing<br>'),
    ('<b>Application Portal:</b>自治体経由 or 直接申請／年間複数回募集（各補助金により異なる）<br>', '<b>Application Portal:</b>Via municipality or direct / Multiple rounds per year (varies by subsidy)<br>'),
    ('<div class="highlight-title"> Google.org Impact Challenge — 中優先度</div>', '<div class="highlight-title">🔍 Google.org Impact Challenge — Medium Priority</div>'),
    ('<b>Application Portal:</b>ウェブ申請（英語必須）／年1回（時期は地域により異なる）<br>', '<b>Application Portal:</b>Web application (English mandatory) / 1 round per year (timing varies by region)<br>'),
    ('<b>Application Portal:</b>ウェブ申請（英語必須）／年1回（通常9月-10月）<br>', '<b>Application Portal:</b>Web application (English mandatory) / 1 round per year (usually Sep-Oct)<br>'),
    ('<b>Application Portal:</b>ウェブ申請（英語必須）／年1回（通常夏季）<br>', '<b>Application Portal:</b>Web application (English mandatory) / 1 round per year (usually summer)<br>'),
    ('<div class="highlight-title">💡 申請のコツ</div>', '<div class="highlight-title">💡 Application Tips</div>'),
    
    # === PAGE 5 TECH ARCHITECTURE ===
    ('<div class="section-title">5. システムアーキテクチャ概要</div>', '<div class="section-title">5. System Architecture Overview</div>'),
    ('<p>LegalShield は <b>「端末優先・サーバー最小」</b>のアーキテクチャを採用し、被害者のプライバシーを保護します。</p>', '<p>LegalShield adopts a <b>"device-first, minimal server"</b> architecture to protect victim privacy.</p>'),
    ('<div class="title">フロントエンド（APP / Web）</div>', '<div class="title">Frontend (APP / Web)</div>'),
    ('<div class="desc">React Native or Flutter（スマホ APP）<br>Streamlit / Next.js（Web 原型）<br>すべての機密データは端末内処理</div>', '<div class="desc">React Native or Flutter (mobile APP)<br>Streamlit / Next.js (web prototype)<br>All sensitive data processed on-device</div>'),
    ('<div class="title">AI エンジン（端末内）</div>', '<div class="title">AI Engine (On-Device)</div>'),
    ('<div class="desc">ONNX Runtime / TensorFlow Lite<br>5重ロール推論モデル<br>オフライン使用可能（地下室・飛行機モード）</div>', '<div class="desc">ONNX Runtime / TensorFlow Lite<br>5-role inference model<br>Offline capable (basement, airplane mode)</div>'),
    ('<div class="title">ベクトルデータベース（端末 + サーバー）</div>', '<div class="title">Vector Database (Device + Server)</div>'),
    ('<div class="desc">LanceDB（端末キャッシュ）<br>623K 国法・724K 判例・885 統計テーブル<br>RAG 即時検索</div>', '<div class="desc">LanceDB (device cache)<br>623K laws · 724K precedents · 885 stat tables<br>Instant RAG search</div>'),
    ('<div class="title">バックエンド（サーバー）</div>', '<div class="title">Backend (Server)</div>'),
    ('<div class="desc">FastAPI + Python<br>AWS Tokyo Region<br>匿名化統計・最小必要データのみ保存</div>', '<div class="desc">FastAPI + Python<br>AWS Tokyo Region<br>Anonymized stats only · minimal data stored</div>'),
    
    ('<div class="section-title">5.1 データベースを APP にするには？</div>', '<div class="section-title">5.1 How to Embed the Database into an APP?</div>'),
    ('<p><b>Step 1: APP フレームワークの選択</b></p>', '<p><b>Step 1: Choose an APP Framework</b></p>'),
    ('<tr><th>フレームワーク</th><th>メリット</th><th>デメリット</th><th>推奨度</th></tr>', '<tr><th>Framework</th><th>Pros</th><th>Cons</th><th>Rating</th></tr>'),
    ('<tr><td><b>Flutter</b></td><td>1つのコードで iOS + Android、高性能、UI 柔軟</td><td>Dart 言語の学習が必要</td><td>⭐⭐⭐⭐⭐</td></tr>', '<tr><td><b>Flutter</b></td><td>Single codebase for iOS + Android, high performance, flexible UI</td><td>Requires learning Dart</td><td>⭐⭐⭐⭐⭐</td></tr>'),
    ('<tr><td><b>React Native</b></td><td>JavaScript エコシステム、開発者が多い、ライブラリ豊富</td><td>性能やや劣る、バージョン断片化</td><td>⭐⭐⭐⭐</td></tr>', '<tr><td><b>React Native</b></td><td>JavaScript ecosystem, many developers, rich libraries</td><td>Slightly lower performance, version fragmentation</td><td>⭐⭐⭐⭐</td></tr>'),
    ('<tr><td><b>PWA</b></td><td>Web 技術のみ、ストア審査不要、最速リリース</td><td>ネイティブ API 制限あり（Bluetooth・NFC など）</td><td>⭐⭐⭐</td></tr>', '<tr><td><b>PWA</b></td><td>Web tech only, no store review, fastest release</td><td>Limited native API access (Bluetooth, NFC, etc.)</td><td>⭐⭐⭐</td></tr>'),
    
    ('<p><b>Step 2: 端末内 AI 推論（オフライン使用可能）</b></p>', '<p><b>Step 2: On-Device AI Inference (Offline Capable)</b></p>'),
    ('<p><b>Step 3: ベクトルデータベースの端末組み込み</b></p>', '<p><b>Step 3: Embed Vector Database on Device</b></p>'),
    ('<p><b>Step 4: 証拠保全モジュール</b></p>', '<p><b>Step 4: Evidence Preservation Module</b></p>'),
    
    ('証拠写真・録音・対話記録：<b>AES-256-GCM 端末内暗号化</b><br>', 'Evidence photos, recordings, dialogue records: <b>AES-256-GCM on-device encryption</b><br>'),
    ('同様に改竄不可能なメタデータ（EXIF + デジタル署名）を自動付加', 'Auto-attach tamper-proof metadata (EXIF + digital signature)'),
    ('<p><b>Step 5: GPS 連動機能</b></p>', '<p><b>Step 5: GPS Linked Functions</b></p>'),
    ('用途：最寄り支援機関検索・緊急時位置送信・証拠 GPS タグ付け', 'Use: nearest support search, emergency location send, evidence GPS tagging'),
    ('<p><b>Step 6: プライバシー・セキュリティ設計</b></p>', '<p><b>Step 6: Privacy & Security Design</b></p>'),
    ('端末内推論でサーバーに個人情報が流出しない', 'On-device inference prevents personal info leaking to servers'),
    ('匿名化統計のみをサーバーに送信', 'Only anonymized statistics sent to server'),
    ('サーバー側は復号不可能（AES-256-GCM + ユーザーパスワード-derived key）', 'Server cannot decrypt (AES-256-GCM + user password-derived key)'),
    
    # === PAGE 6 MOBILE ===
    ('<!-- PAGE 6: スマホ機能連携 -->', '<!-- PAGE 6: Mobile Integration -->'),
    ('<div class="tagline">スマホ機能連携（GPS・カメラ・マイク・SMS）</div>', '<div class="tagline">Mobile Integration (GPS, Camera, Mic, SMS)</div>'),
    ('<div class="section-title">6. スマホネイティブ機能の活用</div>', '<div class="section-title">6. Leveraging Smartphone Native Features</div>'),
    ('<p>LegalShield APP は被害者のスマホのネイティブ機能を最大限に活用し、迅速・安全な証拠保全と緊急対応を実現します。</p>', '<p>The LegalShield APP maximizes smartphone native features for rapid, secure evidence preservation and emergency response.</p>'),
    ('<tr><th>機能</th><th>iOS 実装</th><th>Android 実装</th></tr>', '<tr><th>Feature</th><th>iOS Implementation</th><th>Android Implementation</th></tr>'),
    ('<tr><td>GPS / 位置情報</td><td><code>CoreLocation</code></td><td><code>FusedLocationProvider</code></td></tr>', '<tr><td>GPS / Location</td><td><code>CoreLocation</code></td><td><code>FusedLocationProvider</code></td></tr>'),
    ('<tr><td>カメラ</td><td><code>UIImagePickerController</code></td><td><code>CameraX</code></td></tr>', '<tr><td>Camera</td><td><code>UIImagePickerController</code></td><td><code>CameraX</code></td></tr>'),
    ('<tr><td>マイク</td><td><code>AVAudioRecorder</code></td><td><code>MediaRecorder</code></td></tr>', '<tr><td>Microphone</td><td><code>AVAudioRecorder</code></td><td><code>MediaRecorder</code></td></tr>'),
    ('<tr><td>SMS</td><td>特別な宣言不要（システム SMS App を呼び出す）</td><td><code>SEND_SMS</code></td></tr>', '<tr><td>SMS</td><td>No special declaration needed (calls system SMS app)</td><td><code>SEND_SMS</code></td></tr>'),
    ('<tr><td>通知</td><td><code>UNUserNotificationCenter</code></td><td><code>POST_NOTIFICATIONS</code></td></tr>', '<tr><td>Notifications</td><td><code>UNUserNotificationCenter</code></td><td><code>POST_NOTIFICATIONS</code></td></tr>'),
    ('<tr><td>生体認証</td><td><code>NSFaceIDUsageDescription</code></td><td><code>USE_BIOMETRIC</code></td></tr>', '<tr><td>Biometrics</td><td><code>NSFaceIDUsageDescription</code></td><td><code>USE_BIOMETRIC</code></td></tr>'),
    
    ('<div class="title">📚 技術相談・開発者募集</div>', '<div class="title">📚 Technical Consultation & Developer Recruitment</div>'),
    ('<div class="item">LegalShield は Flutter / React Native エンジニア、AI エンジニア、セキュリティエンジニアを募集しています。</div>', '<div class="item">LegalShield is recruiting Flutter / React Native engineers, AI engineers, and security engineers.</div>'),
    ('<div class="item"><span class="label">技術相談：</span>kenji@hiiforest.com（件名に「技術相談」と記載）</div>', '<div class="item"><span class="label">Technical Inquiry:</span> kenji@hiiforest.com (Subject: "Technical Inquiry")</div>'),
    ('<div class="item"><span class="label">オープンソース貢献：</span>github.com/Fuilko/lawandbabysupport（PR 歓迎）</div>', '<div class="item"><span class="label">Open Source Contribution:</span> github.com/Fuilko/lawandbabysupport (PRs welcome)</div>'),
    
    # Footer
    ('LegalShield Civic Tech Project | 2026年5月<br>', 'LegalShield Civic Tech Project | May 2026<br>'),
    ('「誰も1人にはしない」', '"No One Should Face It Alone"'),
    
    # Page 1 intro remaining
    ('<p style="margin-top:8px">日本では年間 <b>200万人以上</b> が犯罪や権利侵害に遭いますが、その <b>70%</b> say "I don\'t know who to talk to," "I don\'t have time to save evidence," or "I\'m afraid the police will refuse to file my report"— they suffer alone. LegalShield was born to break that invisible wall.</p>', '<p style="margin-top:8px">In Japan, over <b>2 million people</b> fall victim to crimes or rights violations annually, but <b>70%</b> say "I don\'t know who to talk to," "I don\'t have time to save evidence," or "I\'m afraid the police will refuse to file my report"— they suffer alone. LegalShield was born to break that invisible wall.</p>'),
    
    # Page 2 17 crime types table headers already translated, but check remaining
    ('<tr><th>#</th><th>タイプ</th><th>日本の法条</th><th>黄金時間</th></tr>', '<tr><th>#</th><th>Type</th><th>Japanese Law</th><th>Golden Hours</th></tr>'),
    ('<tr><td>1</td><td>配偶者暴力（DV）</td><td>刑法204条・配偶者暴力防止法</td><td>直後</td></tr>', '<tr><td>1</td><td>Domestic Violence (DV)</td><td>Penal Code Art.204 · DV Prevention Act</td><td>Immediately</td></tr>'),
    ('<tr><td>2</td><td>性暴力</td><td>刑法176-178条の2</td><td>直後</td></tr>', '<tr><td>2</td><td>Sexual Violence</td><td>Penal Code Arts.176-178-2</td><td>Immediately</td></tr>'),
    ('<tr><td>3</td><td>消費者被害・詐欺</td><td>刑法246条・組織的犯罪処罰法</td><td>72時間</td></tr>', '<tr><td>3</td><td>Consumer Fraud / Scam</td><td>Penal Code Art.246 · Organized Crime Punishment Act</td><td>72 hours</td></tr>'),
    ('<tr><td>4</td><td>職場パワーハラスメント</td><td>労基法99条・パワハラ防止法</td><td>継続的</td></tr>', '<tr><td>4</td><td>Workplace Power Harassment</td><td>Labor Standards Act Art.99 · Power Harassment Prevention Act</td><td>Ongoing</td></tr>'),
    ('<tr><td>5</td><td>児童虐待</td><td>児童虐待防止法・児童福祉法</td><td>直後</td></tr>', '<tr><td>5</td><td>Child Abuse</td><td>Child Abuse Prevention Act · Child Welfare Act</td><td>Immediately</td></tr>'),
    ('<tr><td>6</td><td>サイバー犯罪・ネットいじめ</td><td>刑法230条・231条</td><td>24時間</td></tr>', '<tr><td>6</td><td>Cybercrime / Online Bullying</td><td>Penal Code Arts.230 · 231</td><td>24 hours</td></tr>'),
    ('<tr><td>7</td><td>ストーカー・つきまとい</td><td>ストーカー規制法・刑法222条</td><td>直後</td></tr>', '<tr><td>7</td><td>Stalking</td><td>Stalker Regulation Act · Penal Code Art.222</td><td>Immediately</td></tr>'),
    ('<tr><td>8</td><td>薬物被害・依存</td><td>覚せい剤取締法等</td><td>継続的</td></tr>', '<tr><td>8</td><td>Drug Victimization / Addiction</td><td>Stimulants Control Act, etc.</td><td>Ongoing</td></tr>'),
    ('<tr><td>9</td><td>ヘイトクライム・差別</td><td>ヘイトスピーチ規制法</td><td>24時間</td></tr>', '<tr><td>9</td><td>Hate Crime / Discrimination</td><td>Hate Speech Regulation Act</td><td>24 hours</td></tr>'),
    ('<tr><td>10</td><td>売買春・人身取引</td><td>売買春防止法・刑法226条の2</td><td>直後</td></tr>', '<tr><td>10</td><td>Human Trafficking</td><td>Prostitution Prevention Act · Penal Code Art.226-2</td><td>Immediately</td></tr>'),
    ('<tr><td>11</td><td>監禁・監視</td><td>刑法220条</td><td>直後</td></tr>', '<tr><td>11</td><td>Illegal Confinement / Surveillance</td><td>Penal Code Art.220</td><td>Immediately</td></tr>'),
    ('<tr><td>12</td><td>器物損壊</td><td>刑法261条</td><td>直後</td></tr>', '<tr><td>12</td><td>Property Damage</td><td>Penal Code Art.261</td><td>Immediately</td></tr>'),
    ('<tr><td>13</td><td>脅迫・恐喝</td><td>刑法222条</td><td>直後</td></tr>', '<tr><td>13</td><td>Threats / Extortion</td><td>Penal Code Art.222</td><td>Immediately</td></tr>'),
    ('<tr><td>14</td><td>不正アクセス・情報漏洩</td><td>不正アクセス禁止法</td><td>72時間</td></tr>', '<tr><td>14</td><td>Unauthorized Access / Data Breach</td><td>Unauthorized Access Prohibition Act</td><td>72 hours</td></tr>'),
    ('<tr><td>15</td><td>ディープフェイク・AI 悪用</td><td>刑法175条・肖像権</td><td>24時間</td></tr>', '<tr><td>15</td><td>Deepfake / AI Misuse</td><td>Penal Code Art.175 · Portrait Rights</td><td>24 hours</td></tr>'),
    ('<tr><td style="color:#c0392b;font-weight:700">16</td><td style="color:#c0392b;font-weight:700">痴漢・公共交通内性犯罪</td><td>刑法176条・迷惑防止条例</td><td>直後</td></tr>', '<tr><td style="color:#c0392b;font-weight:700">16</td><td style="color:#c0392b;font-weight:700">Molestation / Transit Sexual Crime</td><td>Penal Code Art.176 · Nuisance Prevention Ordinances</td><td>Immediately</td></tr>'),
    ('<tr><td style="color:#c0392b;font-weight:700">17</td><td style="color:#c0392b;font-weight:700">公然わいせつ・露出狂</td><td>刑法174条・迷惑防止条例</td><td>直後</td></tr>', '<tr><td style="color:#c0392b;font-weight:700">17</td><td style="color:#c0392b;font-weight:700">Indecent Exposure</td><td>Penal Code Art.174 · Nuisance Prevention Ordinances</td><td>Immediately</td></tr>'),
    
    # 防吃案 unique
    ('<div class="highlight-title">🛡️ 独自機能：被害届不受理防止</div>', '<div class="highlight-title">🛡️ Unique Feature: Anti-Grafting (Prevent Case Dismissal)</div>'),
    ('被害者が警察署に行く前に、AI が「法的根拠レポート」と「警察交渉スクリプト」を自動生成：<br>', 'Before the victim goes to the police station, AI auto-generates a "Legal Basis Report" and "Police Negotiation Script":<br>'),
    ('• 警察「これは民事です」→ あなたは刑法条文で反論<br>', '• Police: "This is civil." → You counter with the applicable Penal Code article.<br>'),
    ('• 警察「証拠が不十分です」→ あなたは被害届受理に証拠完備性は不要と説明<br>', '• Police: "Insufficient evidence." → You explain that filing a report does NOT require complete evidence.<br>'),
    ('• 警察「相談で記録します」→ あなたは正式な受理番号を要求<br>', '• Police: "We\'ll record it as a consultation." → You demand a formal acceptance number.<br>'),
    ('それでも不受理なら、AI が「公安委員会申立書」「検察審査会申立書」を自動生成します。', 'If still refused, AI auto-generates complaints to the Prefectural Public Safety Commission and the Prosecution Review Board.'),
    
    # 今後追加予定
    ('<div class="highlight-title">📋 今後追加予定：民事・行政法分野（2026年後半〜）</div>', '<div class="highlight-title">📋 Future Expansion: Civil & Administrative Law (H2 2026~)</div>'),
    ('<b>刑法</b>だけでなく、<b>製造物責任法（PL法）</b>・<b>労働法侵害</b>・<b>売買契約不履行</b>・<b>背任・信託法違反</b>・<b>環境法違反</b>・<b>行政不服申立て</b>も対応予定。<br>', 'In addition to <b>criminal law</b>, we plan to cover <b>Product Liability (PL)</b>, <b>Labor Law Violations</b>, <b>Breach of Sales Contract</b>, <b>Breach of Trust</b>, <b>Environmental Law</b>, and <b>Administrative Appeals</b>.<br>'),
    ('開発者（高知大学修士・博士進学予定）は、日本の研究データベース権限を活かして判例研究を深化させ、すべての「被害」を「刑事・民事・行政」の三法域でカバーします。', 'The developer (Kochi Univ. Master\'s, PhD candidate) leverages Japan\'s research database access to deepen precedent analysis, covering all "victimizations" across Criminal, Civil, and Administrative law.'),
    
    # Page 5 remaining
    ('<tr><td><b>React Native</b></td><td>JavaScript エコシステム、開発者が多い、ライブラリ豊富</td><td>性能やや劣る、バージョン断片化</td><td>⭐⭐⭐⭐</td></tr>', '<tr><td><b>React Native</b></td><td>JavaScript ecosystem, many developers, rich libraries</td><td>Slightly lower performance, version fragmentation</td><td>⭐⭐⭐⭐</td></tr>'),
]

for old_text, new_text in replacements:
    content = content.replace(old_text, new_text)

with open('LEGALSHIELD_INTRO_EN.html', 'w', encoding='utf-8') as f:
    f.write(content)

import re
cjk = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', content)
print(f'Done. Remaining CJK chars: {len(cjk)}')
