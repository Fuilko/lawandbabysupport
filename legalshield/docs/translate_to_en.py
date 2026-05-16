#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Translate LEGALSHIELD_INTRO_JP.html to English"""

import re

with open('LEGALSHIELD_INTRO_JP.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Define replacements as list of (old_text, new_text)
# Order matters: longer matches first to avoid partial replacements
replacements = [
    # ===== META & HEADER =====
    ('<title>LegalShield — 自己紹介・機能説明・申請ガイド</title>', '<title>LegalShield — Self-Introduction, Features & Application Guide</title>'),
    ('<html lang="ja">', '<html lang="en">'),
    
    # ===== NAVIGATION =====
    ('<a href="#p1">1. 自己紹介</a>', '<a href="#p1">1. Self-Introduction</a>'),
    ('<a href="#p2">2. 機能</a>', '<a href="#p2">2. Features</a>'),
    ('<a href="#p3">3. 開発の経緯</a>', '<a href="#p3">3. Development Story</a>'),
    ('<a href="#p4">4. 申請窓口・メール・パイプライン一覧</a>', '<a href="#p4">4. Grant Application & Partnership Pipeline</a>'),
    ('<a href="#p5">5. 技術アーキテクチャ</a>', '<a href="#p5">5. Tech Architecture</a>'),
    ('<a href="#p6">6. スマホ機能連携</a>', '<a href="#p6">6. Mobile Integration</a>'),
    
    # ===== PAGE 1 =====
    ('<div class="tagline">自己紹介・機能・申請ガイド</div>', '<div class="tagline">Self-Introduction, Features & Application Guide</div>'),
    ('<div class="section-title">1. 自己紹介 — LegalShield とは？</div>', '<div class="section-title">1. Self-Introduction — What is LegalShield?</div>'),
    ('<b>LegalShield</b> は、AI を中核とした<strong>犯罪被害者・権利侵害被害者</strong>向けの無料支援システムです。', '<b>LegalShield</b> is a FREE AI-powered support system for <strong>crime victims and rights violation victims</strong>.'),
    ('が「誰に相談すればいいかわからない」「証拠を保存する時間がない」「被害届が不受理になるのが怖い」', 'say "I don\'t know who to talk to," "I don\'t have time to save evidence," or "I\'m afraid the police will refuse to file my report"'),
    ('と、1人で抱え込んでいます。LegalShield は、その無形の壁を壊すために生まれました。', '— they suffer alone. LegalShield was born to break that invisible wall.'),
    ('<div class="highlight-title">核心理念</div>', '<div class="highlight-title">Core Mission</div>'),
    ('被害者が法律の専門家になる必要はありません。<br>', 'Victims do not need to become legal experts.<br>'),
    ('AI が状況を整理し、証拠を保全し、法律を分析し、戦略をシミュレーションし、専家を紹介する——<br>', 'AI organizes the situation, preserves evidence, analyzes law, simulates strategy, and refers experts — <br>'),
    ('すべての被害者が、事件発生後の「黄金時間」内に、正しい次の一歩を踏み出せるように。', 'so every victim can take the right next step within the "golden hours" after an incident.'),
    
    ('<div class="title">24時間・無料・匿名</div>', '<div class="title">24/7 · Free · Anonymous</div>'),
    ('<div class="desc">本名や住所の登録不要。スマホを開けばすぐに使えます。</div>', '<div class="desc">No real name or address required. Open your phone and use it instantly.</div>'),
    ('<div class="title">AI 5重ロールシステム</div>', '<div class="title">AI 5-Role System</div>'),
    ('<div class="desc">緊急対応、証拠保全、法律分析、戦略シミュレーション、専家紹介をワンストップで。</div>', '<div class="desc">Emergency response, evidence preservation, legal analysis, strategy simulation, and expert referral — all in one.</div>'),
    ('<div class="title">被害届不受理防止機能</div>', '<div class="title">Anti-Grafting Feature</div>'),
    ('<div class="desc">AI が法的根拠付きレポートと警察交渉スクリプトを生成し、被害届不受理を防ぎます。</div>', '<div class="desc">AI auto-generates legal-basis reports and police negotiation scripts to prevent case dismissal.</div>'),
    ('<div class="title">日本最大級の法律データベース</div>', '<div class="title">Japan\'s Largest Legal Database</div>'),
    ('<div class="desc">国法 623K 件、判例 724K 件、e-Stat 統計 885 テーブルを RAG で即時検索。</div>', '<div class="desc">623K national laws, 724K precedents, 885 e-Stat tables — instant RAG search.</div>'),
    
    ('<div class="section-title">基本情報</div>', '<div class="section-title">Basic Information</div>'),
    ('<tr><th>項目</th><th>内容</th></tr>', '<tr><th>Item</th><th>Details</th></tr>'),
    ('<tr><td>プロジェクト名</td><td>LegalShield Civic Tech Project</td></tr>', '<tr><td>Project Name</td><td>LegalShield Civic Tech Project</td></tr>'),
    ('<tr><td>連絡先</td><td><b>kenji@hiiforest.com</b></td></tr>', '<tr><td>Contact</td><td><b>kenji@hiiforest.com</b></td></tr>'),
    ('<tr><td>GitHub</td><td>github.com/Fuilko/lawandbabysupport</td></tr>', '<tr><td>GitHub</td><td>github.com/Fuilko/lawandbabysupport</td></tr>'),
    ('<tr><td>対応言語</td><td>日本語（繁体中文・英語は開発中）</td></tr>', '<tr><td>Languages</td><td>Japanese (Traditional Chinese & English in development)</td></tr>'),
    ('<tr><td>対応地域</td><td>日本 47 都道府県（GPS 連動）</td></tr>', '<tr><td>Coverage</td><td>All 47 prefectures of Japan (GPS-linked)</td></tr>'),
    ('<tr><td>費用</td><td><span class="badge badge-green">被害者完全無料</span></td></tr>', '<tr><td>Cost</td><td><span class="badge badge-green">100% FREE for Victims</span></td></tr>'),
    ('<tr><td>データ処理</td><td><span class="badge badge-blue">端末内 AI 処理・サーバー最小アップロード</span></td></tr>', '<tr><td>Data Processing</td><td><span class="badge badge-blue">On-device AI · Minimal Server Upload</span></td></tr>'),
    
    # ===== PAGE 2 =====
    ('<div class="tagline">機能概要</div>', '<div class="tagline">Feature Overview</div>'),
    ('<div class="section-title">2. 主要機能</div>', '<div class="section-title">2. Key Features</div>'),
    ('<div class="section-body">\n      <p><b>LegalShield</b> は被害者のために、5つの専門家ロールを AI が同時に果たします。</p>', '<div class="section-body">\n      <p><b>LegalShield</b> simultaneously performs 5 expert roles for victims.</p>'),
    ('<tr><th>#</th><th>ロール</th><th>説明</th><th>技術</th></tr>', '<tr><th>#</th><th>Role</th><th>Description</th><th>Tech</th></tr>'),
    ('<tr><td>1</td><td><b>🚨 緊急応変官</b></td><td>一鍵で 110・#8898・#7119 に通報。GPS 位置情報を自動共有。無音モード対応。</td><td>Swift 緊急通報 API / Android EmergencyManager</td></tr>', '<tr><td>1</td><td><b>🚨 Emergency Responder</b></td><td>One-touch dial to 110 / #8898 / #7119. Auto GPS sharing. Silent mode supported.</td><td>Swift Emergency API / Android EmergencyManager</td></tr>'),
    ('<tr><td>2</td><td><b>📁 証拠保全官</b></td><td>写真・録音・LINE 履歴を自動整理。SHA-256 ハッシュ付きの保全証明書発行。裁判所提出可能。</td><td>Exif タイムスタンプ・AES-256-GCM 暗号化</td></tr>', '<tr><td>2</td><td><b>📁 Evidence Collector</b></td><td>Auto-organizes photos, recordings, LINE history. SHA-256 hashed preservation certificate. Court-admissible.</td><td>Exif timestamp · AES-256-GCM encryption</td></tr>'),
    ('<tr><td>3</td><td><b>⚖️ 法律分析師</b></td><td>623K 国法 + 724K 判例 + 885 統計テーブルを RAG で即時検索。あなたの状況に最も適した法条を提示。</td><td>LanceDB ベクトル検索・LangChain RAG・ONNX Runtime</td></tr>', '<tr><td>3</td><td><b>⚖️ Legal Analyst</b></td><td>Instant RAG search across 623K laws + 724K precedents + 885 stat tables. Relevant articles tailored to your situation.</td><td>LanceDB vector search · LangChain RAG · ONNX Runtime</td></tr>'),
    ('<tr><td>4</td><td><b>🧭 戦略模擬師</b></td><td>刑事告訴・民事訴訟・ADR・行政申立・刑事告発の5つの道を比較。時間・費用・成功率をシミュレーション。</td><td>条件付き確率モデル・コスト推定アルゴリズム</td></tr>', '<tr><td>4</td><td><b>🧭 Strategy Simulator</b></td><td>Compares 5 paths: criminal complaint, civil suit, ADR, administrative appeal, criminal report. Simulates time, cost, and success rate.</td><td>Conditional probability model · Cost estimation algorithm</td></tr>'),
    ('<tr><td>5</td><td><b>🗺️ 転介導航員</b></td><td>GPS 連動で最寄りの弁護士・NPO・シェルターを検索。予約スクリプト・書類チェックリスト付き。</td><td>Geolocation API・Google Places API・全国ホットラインデータベース</td></tr>', '<tr><td>5</td><td><b>🗺️ Referral Navigator</b></td><td>GPS-linked nearest lawyer, NPO, and shelter search. Includes booking scripts and document checklists.</td><td>Geolocation API · Google Places API · National hotline DB</td></tr>'),
    
    ('<div class="section-title">2.2 17類型犯罪分類学（拡張版）</div>', '<div class="section-title">2.2 Extended Crime Taxonomy (17 Types)</div>'),
    ('<div class="section-body">\n      <p>被害者が「自分の被害はどの類型か」を判断できない。LegalShield は、17類型の犯罪について「法的根拠」「黄金時間」「証拠の保存方法」を自動提示します。</p>\n    </div>', '<div class="section-body">\n      <p>Victims often cannot identify their incident type. LegalShield auto-suggests "legal basis," "golden hours," and "evidence preservation methods" for 17 crime types.</p>\n    </div>'),
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
    
    ('<div class="highlight-title">📋 今後追加予定：民事・行政法分野（2026年後半〜）</div>', '<div class="highlight-title">📋 Future Expansion: Civil & Administrative Law (H2 2026~)</div>'),
    ('<b>刑法</b>だけでなく、<b>製造物責任法（PL法）</b>・<b>労働法侵害</b>・<b>売買契約不履行</b>・<b>背任・信託法違反</b>・<b>環境法違反</b>・<b>行政不服申立て</b>も対応予定。<br>', 'In addition to <b>criminal law</b>, we plan to cover <b>Product Liability (PL)</b>, <b>Labor Law Violations</b>, <b>Breach of Sales Contract</b>, <b>Breach of Trust</b>, <b>Environmental Law</b>, and <b>Administrative Appeals</b>.<br>'),
    ('開発者（高知大学修士・博士進学予定）は、日本の研究データベース権限を活かして判例研究を深化させ、すべての「被害」を「刑事・民事・行政」の三法域でカバーします。', 'The developer (Kochi Univ. Master\'s, PhD candidate) leverages Japan\'s research database access to deepen precedent analysis, covering all "victimizations" across Criminal, Civil, and Administrative law.'),
    
    ('<div class="highlight-title">🛡️ 独自機能：被害届不受理防止</div>', '<div class="highlight-title">🛡️ Unique Feature: Anti-Grafting (Prevent Case Dismissal)</div>'),
    ('被害者が警察署に行く前に、AI が「法的根拠レポート」と「警察交渉スクリプト」を自動生成：<br>', 'Before the victim goes to the police station, AI auto-generates a "Legal Basis Report" and "Police Negotiation Script":<br>'),
    ('• 警察「これは民事です」→ あなたは刑法条文で反論<br>', '• Police: "This is civil." → You counter with the applicable Penal Code article.<br>'),
    ('• 警察「証拠が不十分です」→ あなたは被害届受理に証拠完備性は不要と説明<br>', '• Police: "Insufficient evidence." → You explain that filing a report does NOT require complete evidence.<br>'),
    ('• 警察「相談で記録します」→ あなたは正式な受理番号を要求<br>', '• Police: "We\'ll record it as a consultation." → You demand a formal acceptance number.<br>'),
    ('それでも不受理なら、AI が「公安委員会申立書」「検察審査会申立書」を自動生成します。', 'If still refused, AI auto-generates complaints to the Prefectural Public Safety Commission and the Prosecution Review Board.'),
]

for old_text, new_text in replacements:
    content = content.replace(old_text, new_text)

with open('LEGALSHIELD_INTRO_EN.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('EN version created: LEGALSHIELD_INTRO_EN.html')
print(f'Total chars: {len(content):,}')
