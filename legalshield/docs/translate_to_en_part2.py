#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Supplemental translations for LEGALSHIELD_INTRO_EN.html"""

with open('LEGALSHIELD_INTRO_EN.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    # Page 1 remaining
    ('<div class="tagline">「誰も1人にはしない」</div>', '<div class="tagline">"No One Should Face It Alone"</div>'),
    ('<div class="subtitle">AI 被害者支援システム | Civic Tech Project | 公益×テクノロジー</div>', '<div class="subtitle">AI Victim Support System | Civic Tech Project | Social Good × Technology</div>'),
    ('<div class="toc-title">目次</div>', '<div class="toc-title">Table of Contents</div>'),
    ('<a href="#p2">2. 機能紹介（17類型犯罪 + AI 5重ロール）</a>', '<a href="#p2">2. Features (17 Crime Types + AI 5-Role System)</a>'),
    ('<a href="#p5">5. 技術アーキテクチャとデータベース APP 化ガイド</a>', '<a href="#p5">5. Tech Architecture & Database APP Guide</a>'),
    ('<a href="#p6">6. スマホ機能連携（GPS・カメラ・マイク・SMS）</a>', '<a href="#p6">6. Mobile Integration (GPS, Camera, Mic, SMS)</a>'),
    
    # Page 2 remaining
    ('<div class="tagline">機能概要</div>', '<div class="tagline">Feature Overview</div>'),
    ('LegalShield は被害者のために、5つの専門家ロールを AI が同時に果たします。', 'LegalShield simultaneously performs 5 expert roles for victims.'),
    
    # Page 3 - Developer Profile
    ('<!-- PAGE 3: 開発経緯 -->', '<!-- PAGE 3: Development Story -->'),
    ('<div class="tagline">開発の経緯</div>', '<div class="tagline">Development Story</div>'),
    ('<div class="section-title">3. 開発者プロフィール — なぜ LegalShield を開発したのか？</div>', '<div class="section-title">3. Developer Profile — Why Build LegalShield?</div>'),
    ('<b>開発者：劉建志（Kenji）— 高知大学 森林工学研究室 / 光伊フォレスト（Hi-i Forest Co., Ltd.）</b>', '<b>Developer: Kenji (Liu Chien-Chih) — Kochi University Forestry Lab / Hi-i Forest Co., Ltd.</b>'),
    ('私は元々宇宙を目指していた学生でした。大学では<b>犯罪脳科学</b>、<b>刑法・民法・環境法</b>を学び、環境運動にも積極的に参加していました。', 'I was once a student aiming for space. At university, I studied <b>criminal neuroscience</b>, <b>criminal/civil/environmental law</b>, and actively participated in environmental movements.'),
    ('2018年、台湾の科学技術法科大学院（科法所）への進学を目指し、検察官になる夢を持っていました。', 'In 2018, I aspired to enter Taiwan\'s Graduate Institute of Science & Technology Law, dreaming of becoming a prosecutor.'),
    ('しかし娘が日本で生まれ、家族のために日本に残る決断をしました。', 'But my daughter was born in Japan, and I decided to stay for my family.'),
    ('現在は<b>高知大学で森林工学の修士課程</b>に在籍し、日台双方の法人（光伊フォレスト）を運営。<br>', 'I am currently enrolled in a <b>Master\'s program in Forestry Engineering at Kochi University</b>, operating companies in both Japan and Taiwan (Hi-i Forest).<br>'),
    ('林業コンサル、日台交流事業、さらに<b>リンゴ・NIKE 工場</b>での管理・安全管理の実務経験も持っています。<br>', 'I have practical experience in forestry consulting, Japan-Taiwan exchange business, and management/safety at <b>Apple and NIKE factories</b>.<br>'),
    ('IT 分野では、台湾の<b>TEAMS 5（防ハッキング主要企業）</b>と技術提携し、サイバーセキュリティの知見も持ち合わせています。', 'In IT, I have a technical partnership with Taiwan\'s <b>TEAMS 5</b> (a major anti-hacking company), bringing cybersecurity expertise.'),
    ('⚠️ 開発者自身が被害者であり、訴訟当事者です', '⚠️ The developer himself is a victim and litigation party'),
    ('2026年2月3日、台湾でドローン測量作業中、製品の設計缺陷により墜落。<br>', 'On February 3, 2026, while conducting drone surveying in Taiwan, a design defect caused a crash.<br>'),
    ('調査の過程でメーカーが <b>34 項の安全缺陷</b>を隠蔽していたことが判明しましたが、行政機関・消費者保護体制は無力でした。<br>', 'Investigation revealed the manufacturer concealed <b>34 safety defects</b>, but administrative and consumer protection agencies were powerless.<br>'),
    ('現在、<b>台湾と日本で同時に訴訟・ADR を進行中</b>（背信・商品損壊）。<br>', 'Currently <b>litigating simultaneously in Taiwan and Japan</b> (breach of trust / property damage).<br>'),
    ('高知・大阪・東京と十数社の弁護士を探しましたが、適切な専門家が見つからず、費用も法外でした。', 'I searched over a dozen law firms across Kochi, Osaka, and Tokyo, but could not find affordable specialized help.'),
    ('私のような背景（法律を学んだ、企業経営経験あり、IT にも詳しい）を持つ者でさえ、<b>証拠確鑿の民事・商事訴訟でこれほど苦労する</b>のです。', 'Even someone with my background (law studies, business experience, IT knowledge) <b>struggles this much in civil/commercial litigation with solid evidence</b>.'),
    ('では、法律の知識がない、経済的に余裕がない、地方に住む被害者はどうなるのでしょうか？', 'Then what happens to victims with no legal knowledge, no financial means, living in rural areas?'),
    ('私は<b>高知県・黒潮の郷</b>で4人の娘を育てています。都市と地方の<b>圧倒的な資源格差</b>を身に沁みて感じています。<br>', 'I raise 4 daughters in <b>Kochi Prefecture, the land of the Kuroshio Current</b>. I deeply feel the <b>overwhelming resource gap</b> between urban and rural areas.<br>'),
    ('地方創生は経済だけではありません。<b>法律、医療、正義の実現</b>——これらが地方では極めて困難です。<br>', 'Regional revitalization is not just economics. <b>Law, healthcare, and justice</b> are extremely difficult to access in rural areas.<br>'),
    ('特に女性被害者や子育て中の親にとって、適切な法律支援にアクセスすることは、都市と比べて桁違いに難しいのです。', 'Especially for female victims and parents raising children, accessing proper legal support is orders of magnitude harder than in cities.'),
    ('「公権力が一般市民を守れないとき、<br>テクノロジーは弱者の手の中の武器になるべきだ。」<br>', '"When public power fails to protect citizens,<br>technology must become a weapon in the hands of the weak."<br>'),
    ('— 劉建志（Kenji）、2026年5月', '— Kenji (Liu Chien-Chih), May 2026'),
    
    # 4つの核心観察
    ('<div class="section-title">4つの核心観察</div>', '<div class="section-title">4 Core Observations</div>'),
    ('<div class="title">観察一：制度の隙間</div>', '<div class="title">Observation 1: System Gaps</div>'),
    ('日本には年間200万+ の被害者がいるが、法テラスは平日10-16時、NPO は地域格差があり、', 'Japan has 2M+ victims annually, but Legal Aid is weekdays 10-16 only, NPOs have regional gaps,'),
    ('警察による被害届不受理は頻繁。被害者は「事件発生後 24-72 時間の黄金時間」内に、ほとんど構造化された支援を受けられない。', 'and police case dismissal is frequent. Victims receive almost no structured support within the 24-72 hour "golden time."'),
    ('<div class="title">観察二：テクノロジーの格差</div>', '<div class="title">Observation 2: Tech Inequality</div>'),
    ('企業向け Legal Tech（例：Legalscape）は成熟しているが、対象は「弁護士を雇える企業」。', 'Enterprise Legal Tech (e.g., Legalscape) is mature, but targets "companies that can hire lawyers."'),
    ('一般市民・被害者・弱者こそがテクノロジーから取り残されている。', 'Ordinary citizens, victims, and the vulnerable are the ones left behind by technology.'),
    ('<div class="title">観察三：AI の可能性</div>', '<div class="title">Observation 3: AI Potential</div>'),
    ('2025-2026 年、AI（LLM）は高品質な法律文書分析、戦略シミュレーション、多言語対話が可能になった。', 'In 2025-2026, AI (LLM) became capable of high-quality legal document analysis, strategy simulation, and multilingual dialogue.'),
    ('この能力は大企業だけのものではなく、すべての助けを必要とする人に開放されるべきだ。', 'This capability should not belong only to large corporations — it must be open to everyone who needs help.'),
    ('<div class="title">観察四：都市と地方の格差</div>', '<div class="title">Observation 4: Urban-Rural Gap</div>'),
    ('高知県のような地方では、弁護士・NPO・支援機関へのアクセスが極端に限られる。', 'In rural areas like Kochi Prefecture, access to lawyers, NPOs, and support agencies is extremely limited.'),
    ('女性被害者、子育て中の親、高齢者にとって、東京や大阪の資源は遠く、交通費・時間的制約も圧倒的。', 'For female victims, parents, and the elderly, resources in Tokyo and Osaka are distant, with overwhelming travel costs and time constraints.'),
    ('デジタルで法の力を地方に届けることが急務だ。', 'Delivering the power of law to rural areas digitally is an urgent priority.'),
    
    # 開発の軌跡
    ('<div class="section-title">開発の軌跡</div>', '<div class="section-title">Development Timeline</div>'),
    ('<tr><th>時期</th><th>マイルストーン</th></tr>', '<tr><th>Date</th><th>Milestone</th></tr>'),
    ('開発者自身が台湾でドローン事故に遭い、メーカーの34項安全缺陷を発見。日本の法律・被害者支援体制を研究開始', 'Developer personally experienced a drone accident in Taiwan, discovered 34 safety defects. Began researching Japan\'s legal and victim support systems.'),
    ('LegalShield 構想：AI × 被害者支援 × 被害届不受理防止。自身の訴訟・ADR準備経験と大量証拠管理の知見を結合', 'LegalShield concept: AI × Victim Support × Anti-Grafting. Combined personal litigation/ADR preparation experience with mass evidence management expertise.'),
    ('国法（e-LAWS XML 623K 件）、判例、統計データのクロール開始。高知大学の研究データベース権限を活用', 'Started crawling national laws (e-LAWS XML 623K items), precedents, and statistics. Leveraged Kochi University research database access.'),
    ('ベクトルデータベース（LanceDB）・RAG 検索システム・AI 5重ロール原型完成', 'Completed vector database (LanceDB), RAG search system, and AI 5-role prototype.'),
    ('緊急モード設計・被害届不受理防止機能・17類型犯罪分類学（刑法中心）・加害者プロファイルデータベース完成', 'Completed emergency mode design, anti-grafting feature, 17-type crime taxonomy (criminal law focus), and perpetrator profile database.'),
    ('（予定）助成金申請・パートナー開拓・TEAMS 5 との技術連携強化・パイロット運営開始', '(Planned) Grant applications, partnership development, TEAMS 5 tech collaboration, and pilot operations.'),
    ('（予定）民事法・行政法分野拡張、判例研究の深化、博士課程進学と研究連携', '(Planned) Expansion into civil/administrative law, deeper precedent research, PhD enrollment, and academic collaboration.'),
    
    # 今後の拡張計画
    ('<div class="section-title">今後の拡張計画 — 刑法だけでなく、民事・行政法も</div>', '<div class="section-title">Future Expansion — Beyond Criminal Law to Civil & Administrative Law</div>'),
    ('現在の LegalShield は<b>17類型の犯罪（刑法分野）</b>を中心に構築されていますが、今後は以下の領域へ拡張します：', 'LegalShield currently focuses on <b>17 crime types (criminal law)</b>, but will expand to the following areas:'),
    ('製造物責任法（PL法）', 'Product Liability (PL) Law'),
    ('製品缺陷による被害・リコール対応', 'Product defect damage and recall response'),
    ('労働法侵害', 'Labor Law Violations'),
    ('不当解雇・賃金未払い・労災隠蔽・パワハラ', 'Unfair dismissal, wage non-payment, labor accident concealment, power harassment'),
    ('売買契約不履行', 'Breach of Sales Contract'),
    ('債務不履行・瑕疵担保責任', 'Debt default and warranty liability'),
    ('背任・信託法違反', 'Breach of Trust / Trust Law Violations'),
    ('取締役・役員の背任行為', 'Director/officer breach of trust'),
    ('環境法違反', 'Environmental Law Violations'),
    ('土壌汚染・水質汚染・廃棄物違法投棄', 'Soil/water pollution, illegal waste dumping'),
    ('行政不服申立て', 'Administrative Appeals'),
    ('行政不服申立て・国家賠償・情報公開請求', 'Administrative appeals, state compensation, information disclosure requests'),
    ('判例研究の深化', 'Deepened Precedent Research'),
    ('高知大学のデータベース権限を活かし、各領域の最新判例をリアルタイム統合', 'Leveraging Kochi University database access to integrate latest precedents in real time across all domains.'),
    ('開発者は現在高知大学の修士課程に在籍し、博士課程進学を予定しています。', 'The developer is currently enrolled in a Master\'s program at Kochi University and plans to pursue a PhD.'),
    ('学術研究と Civic Tech の融合を目指し、日本の研究データベースへのフルアクセス権限を活かして、', 'Aiming to integrate academic research and Civic Tech, leveraging full access to Japan\'s research databases to'),
    ('法律 AI の精度と網羅性を飛躍的に高めていきます。', 'dramatically improve the accuracy and comprehensiveness of the legal AI.'),
    
    # 公益先行
    ('<div class="section-title">公益先行、収益は自然に</div>', '<div class="section-title">Social Mission First, Revenue Follows</div>'),
    ('LegalShield のビジネスモデルは <b>「被害者への利用は永久無料」</b>です。収益源は：', 'LegalShield\'s business model is <b>"permanently free for victims."</b> Revenue sources:'),
    ('弁護士・NPO への優質案件導流サブスクリプション', 'Premium case referral subscription for lawyers and NPOs'),
    ('自治体 GovTech SaaS（相談支援システム）', 'Municipal GovTech SaaS (consultation support system)'),
    ('匿名化データ洞察レポート（学術・政策用）', 'Anonymized data insight reports (for academia and policy)'),
    ('被害者向け保険・金融仲介', 'Victim-oriented insurance and financial brokerage'),
    ('社会ミッションが第一、収益はミッションの副産物です。', 'Social mission is paramount; revenue is a byproduct of that mission.'),
    
    # Page 4
    ('<!-- PAGE 4: 申請窓口 -->', '<!-- PAGE 4: Grant Application & Partnership -->'),
    ('<div class="tagline">申請窓口・メール・パイプライン一覧</div>', '<div class="tagline">Application Guide, Email Templates & Pipeline</div>'),
    ('<div class="section-title">4. 助成金・補助金申請窓口</div>', '<div class="section-title">4. Grant & Subsidy Application Windows</div>'),
    ('LegalShield は現在<strong>原型完成・パイロット準備</strong>段階です。実証試験のためのシード資金が必要です。以下の窓口に申請可能です。', 'LegalShield is currently at the <strong>prototype-complete, pilot-ready</strong> stage. Seed funding for proof-of-concept is needed. Applications can be submitted to the following organizations:'),
    ('<tr><th>優先度</th><th>機関名</th><th>金額目安</th><th>申請方法</th><th>適合理由</th></tr>', '<tr><th>Priority</th><th>Organization</th><th>Amount</th><th>How to Apply</th><th>Fit</th></tr>'),
    ('<td><span class="badge badge-red">最高</span></td>', '<td><span class="badge badge-red">Highest</span></td>'),
    ('<td><span class="badge badge-green">高</span></td>', '<td><span class="badge badge-green">High</span></td>'),
    ('<td><span class="badge badge-blue">中</span></td>', '<td><span class="badge badge-blue">Medium</span></td>'),
    ('<td><b>トヨタ財団</b><br>一般助成</td>', '<td><b>Toyota Foundation</b><br>General Grant</td>'),
    ('<td>¥100万-500万</td>', '<td>¥1M-5M</td>'),
    ('<td>ウェブ申請書<br>年1-2回募集</td>', '<td>Web application<br>1-2 rounds/year</td>'),
    ('<td>社会課題解決・テクノロジー活用・人権支援</td>', '<td>Social issue resolution, technology utilization, human rights support</td>'),
    ('<td><b>伊藤園ホールディングス</b><br>社会貢献助成</td>', '<td><b>ITO EN Holdings</b><br>Social Contribution Grant</td>'),
    ('<td>¥50万-300万</td>', '<td>¥500K-3M</td>'),
    ('<td>ウェブ申請書<br>年1回募集</td>', '<td>Web application<br>1 round/year</td>'),
    ('<td>地域社会・人権支援・弱者支援</td>', '<td>Community, human rights, vulnerable group support</td>'),
    ('<td><b>DBJ 日本政策投資銀行</b><br>イノベーション助成</td>', '<td><b>DBJ (Development Bank of Japan)</b><br>Innovation Grant</td>'),
    ('<td>¥500万-2000万</td>', '<td>¥5M-20M</td>'),
    ('<td>ウェブ・担当者窓口<br>随時</td>', '<td>Web / Contact<br>Ongoing</td>'),
    ('<td>Civic Tech・データ活用・社会課題</td>', '<td>Civic Tech, data utilization, social issues</td>'),
    ('<td><b>内閣府 地方創生推進室</b><br>補助金</td>', '<td><b>Cabinet Office Regional Revitalization</b><br>Subsidy</td>'),
    ('<td>¥100万-1000万</td>', '<td>¥1M-10M</td>'),
    ('<td>自治体経由 or 直接<br>随時</td>', '<td>Via municipality or direct<br>Ongoing</td>'),
    ('<td>地方創生・デジタル化・被害者支援</td>', '<td>Regional revitalization, digitalization, victim support</td>'),
    ('<td><b>Google.org Impact Challenge</b></td>', '<td><b>Google.org Impact Challenge</b></td>'),
    ('<td>$10万-50万<br>(約¥1500万-7500万)</td>', '<td>$100K-500K<br>(~¥15M-75M)</td>'),
    ('<td>ウェブ申請<br>年1回</td>', '<td>Web application<br>1 round/year</td>'),
    ('<td>Technology × Social Impact</td>', '<td>Technology × Social Impact</td>'),
    ('<td><b>Microsoft AI for Good</b></td>', '<td><b>Microsoft AI for Good</b></td>'),
    ('<td>$5万-50万<br>(約¥750万-7500万)</td>', '<td>$50K-500K<br>(~¥7.5M-75M)</td>'),
    ('<td>AI × 社会インパクト</td>', '<td>AI × Social Impact</td>'),
    ('<td><b>Meta Community Grants</b></td>', '<td><b>Meta Community Grants</b></td>'),
    ('<td>$1万-10万<br>(約¥150万-1500万)</td>', '<td>$10K-100K<br>(~¥1.5M-15M)</td>'),
    ('<td>安全・人権テック</td>', '<td>Safety & Human Rights Tech</td>'),
    
    # パートナー開拓
    ('<div class="section-title">4.2 パートナー開拓窓口</div>', '<div class="section-title">4.2 Partnership Development</div>'),
    ('<div class="section-body">\n      <p>LegalShield は<strong>弁護士会・NPO・支援施設・自治体・大学</strong>をパートナーとして募集しています。</p>\n    </div>', '<div class="section-body">\n      <p>LegalShield is recruiting <strong>bar associations, NPOs, support facilities, municipalities, and universities</strong> as partners.</p>\n    </div>'),
    ('<tr><th>対象</th><th>窓口</th><th>内容</th></tr>', '<tr><th>Target</th><th>Contact</th><th>Scope</th></tr>'),
    ('<td><b>日本弁護士連合会</b></td>', '<td><b>Japan Federation of Bar Associations</b></td>'),
    ('<td>各都道府県弁護士会<br>担当部門</td>', '<td>Prefectural bar associations<br>Relevant dept.</td>'),
    ('<td>案件導流協定・法律内容監修・被害者相談窓口紹介</td>', '<td>Case referral agreements, legal content review, victim consultation referrals</td>'),
    ('<td><b>法テラス</b></td>', '<td><b>Japan Legal Support Center</b></td>'),
    ('<td>各地方法テラス<br>総務部</td>', '<td>Local legal aid centers<br>General Affairs</td>'),
    ('<td>公設扶助制度連携・無料法律相談窓口の GPS マッチング</td>', '<td>Public aid coordination, GPS matching of free legal consultation windows</td>'),
    ('<td><b>DV支援センター</b><br>（全国約120拠点）</td>', '<td><b>DV Support Centers</b><br>(~120 nationwide)</td>'),
    ('<td>各都道府県<br>DV相談・支援センター</td>', '<td>Prefectural DV counseling & support centers</td>'),
    ('<td>緊急時転介連動・避難所情報 API 化</td>', '<td>Emergency referral linkage, shelter info API integration</td>'),
    ('<td><b>児童相談所</b></td>', '<td><b>Child Consultation Centers</b></td>'),
    ('<td>各市町村<br>児童相談所</td>', '<td>Municipal child consultation centers</td>'),
    ('<td>児童虐待通報・#7119 連動・児童福祉資料統合</td>', '<td>Child abuse reporting, #7119 linkage, child welfare data integration</td>'),
    ('<td><b>大学・研究機関</b></td>', '<td><b>Universities & Research Institutes</b></td>'),
    ('<td>法学部・社会福祉学部<br>犯罪学研究センター</td>', '<td>Law / Social Welfare faculties<br>Criminology research centers</td>'),
    ('<td>学術研究連携・J-STAGE 論文分析・政策提言</td>', '<td>Academic research collaboration, J-STAGE paper analysis, policy recommendations</td>'),
    ('<td><b>自治体</b></td>', '<td><b>Municipalities</b></td>'),
    ('<td>各市町村<br>ICT推進課・市民協働課</td>', '<td>Municipalities<br>ICT Promotion / Civic Collaboration depts.</td>'),
    ('<td>GovTech SaaS 販売・地域被害データ可視化</td>', '<td>GovTech SaaS sales, regional victim data visualization</td>'),
    
    # Contact box
    ('<div class="title">📧 LegalShield 連絡先</div>', '<div class="title">📧 LegalShield Contact</div>'),
    ('<div class="item"><span class="label">プロジェクトメール：</span>kenji@hiiforest.com</div>', '<div class="item"><span class="label">Project Email:</span> kenji@hiiforest.com</div>'),
    ('<div class="item"><span class="label">申請相談：</span>「機関名・希望する提携内容・担当者連絡先」を上記メールまで</div>', '<div class="item"><span class="label">Application Inquiry:</span> Send "Organization name / desired partnership / contact" to the email above</div>'),
    ('<div class="item"><span class="label">返信目安：</span>3営業日以内</div>', '<div class="item"><span class="label">Response:</span> Within 3 business days</div>'),
    
    # 各機関の詳細
    ('<div class="section-title">4.3 各機関の詳細情報・URL・申請アドバイス</div>', '<div class="section-title">4.3 Detailed Organization Info, URLs & Application Advice</div>'),
    ('<div class="highlight-title">🚗 トヨタ財団（一般助成）— 最高優先度</div>', '<div class="highlight-title">🚗 Toyota Foundation (General Grant) — Highest Priority</div>'),
    ('<b>公式URL：</b>', '<b>Official URL:</b>'),
    ('<b>申請窓口：</b>', '<b>Application Portal:</b>'),
    ('<b>連絡先：</b>', '<b>Contact:</b>'),
    ('<b>申請アドバイス：</b>', '<b>Application Advice:</b>'),
    ('• 強みは「社会課題解決 × テクノロジー × 人権」。技術詳細よりも「誰が救われるか」のストーリーを重視。', '• Strength: "Social issue resolution × Technology × Human rights." Focus on "who will be saved" rather than technical details.'),
    ('• 「被害者支援」「地方創生」「女性・子ども支援」のキーワードを含める。', '• Include keywords: "victim support," "regional revitalization," "women & children support."'),
    ('• 実績がない場合は「パイロット計画の具体性」でカバー。高知県での実証試験を強調。', '• If no track record, cover with "concrete pilot plan." Emphasize proof-of-concept in Kochi Prefecture.'),
    ('• 金額は ¥300万-500万が現実的。大きすぎる金額は避ける。', '• Realistic amount: ¥3-5M. Avoid overly large amounts.'),
    ('• 添付：プロジェクト紹介HTML（ONE_PAGER）+ 3分動画 + 代表者プロフィール', '• Attachments: Project intro HTML (ONE_PAGER) + 3-min video + representative profile.'),
    
    ('<div class="highlight-title">🍵 伊藤園ホールディングス（社会貢献助成）— 最高優先度</div>', '<div class="highlight-title">🍵 ITO EN Holdings (Social Contribution Grant) — Highest Priority</div>'),
    ('サステナビリティ推進部（メール問い合わせフォーム経由）', 'Sustainability Promotion Dept (via email inquiry form)'),
    ('• 「自然との共生」「地域社会の発展」「人権尊重」が企業価値と接続する訴求が効く。', '• Appeals connecting to corporate values: "coexistence with nature," "community development," "human rights respect."'),
    ('• 高知県・四国エリアの地方創生と結びつける。都市部だけでなく地方の課題解決をアピール。', '• Tie to regional revitalization in Kochi / Shikoku. Appeal to solving rural, not just urban, problems.'),
    ('• 「子育て中の親」「女性被害者」など、具体的な受益者像を描く。', '• Depict concrete beneficiary personas: "parents raising children," "female victims."'),
    ('• 金額は ¥100万-300万が適切。飲料業界の社会貢献イメージと合致させる。', '• Appropriate amount: ¥1-3M. Align with beverage industry social contribution image.'),
    
    ('<div class="highlight-title">🏦 DBJ 日本政策投資銀行（イノベーション助成）— 高優先度</div>', '<div class="highlight-title">🏦 DBJ (Innovation Grant) — High Priority</div>'),
    ('各支店の「新規事業・イノベーション担当」または本店企画部', 'Branch "New Business / Innovation" contact or HQ Planning Dept.'),
    ('• Civic Tech × データ活用 × 社会課題解決の「事業性」を重視。収益モデル（B2B2G）を明確に示す。', '• Emphasize "business viability" of Civic Tech × Data × Social Issue Resolution. Clearly show revenue model (B2B2G).'),
    ('• 5年後の収益予測（¥5億/年）と「被害者永久無料」の両立を説明。', '• Explain how ¥500M/year revenue in 5 years coexists with "permanently free for victims."'),
    ('• チームの技術力（TEAMS 5 提携含む）と学術的背景（高知大学）を強調。', '• Highlight team technical capability (incl. TEAMS 5 partnership) and academic background (Kochi University).'),
    ('• 金額は ¥500万-2000万が現実的。事業計画書（BP）の質が勝負。', '• Realistic amount: ¥5-20M. Business plan quality determines success.'),
    ('• 面談の機会を作ることが重要。まず「事業相談」として担当者と接触する。', '• Creating face-to-face opportunities is crucial. First approach as a "business consultation."'),
    
    ('<div class="highlight-title">🏛️ 内閣府 地方創生推進室（補助金）— 高優先度</div>', '<div class="highlight-title">🏛️ Cabinet Office Regional Revitalization (Subsidy) — High Priority</div>'),
    ('内閣府地方創生推進事務局 03-3581-4111', 'Cabinet Office Regional Revitalization Bureau 03-3581-4111'),
    ('• 「地方創生交付金」「デジタル田園都市構想」など、複数の補助金枠が存在。', '• Multiple subsidy frameworks exist: "Regional Revitalization Grants," "Digital Rural-Urban Concept," etc.'),
    ('• 高知県を通じて自治体経由で申請するのが最も現実的。高知県庁の「ICT推進課」にまず相談。', '• Most realistic route: apply via Kochi Prefecture. First consult Kochi Pref. ICT Promotion Dept.'),
    ('• 「高知県内の被害者支援」「デジタル化による行政効率化」を訴求。', '• Appeal: "Victim support within Kochi Prefecture" and "administrative efficiency through digitalization."'),
    ('• GovTech SaaS の自治体導入実績があれば、さらに説得力が増す。', '• GovTech SaaS adoption track record by municipalities adds further persuasiveness.'),
    
    ('<div class="highlight-title">🔍 Google.org Impact Challenge — 中優先度</div>', '<div class="highlight-title">🔍 Google.org Impact Challenge — Medium Priority</div>'),
    ('オンラインフォームのみ（直接メールは非推奨）', 'Online form only (direct email not recommended)'),
    ('• <b>英語申請必須。</b>日本語では受け付けられない。英文版プロジェクト紹介（ONE_PAGER_EN）が必要。', '• <b>English application mandatory.</b> Japanese not accepted. English project intro (ONE_PAGER_EN) required.'),
    ('• 「Technology × Social Impact」の明確な接続が必要。AI の具体例（端末内推論・RAG検索）を示す。', '• Clear connection of "Technology × Social Impact" required. Show concrete AI examples (on-device inference, RAG search).'),
    ('• 「スケーラビリティ」を重視。日本だけでなくアジア展開の可能性を匂わせる。', '• Emphasize "scalability." Hint at Asia expansion potential, not just Japan.'),
    ('• 金額は $10万-50万（約¥1500万-7500万）。インパクト指標（KPI）を数字で具体的に示す。', '• Amount: $100K-500K (~¥15M-75M). Show impact KPIs in concrete numbers.'),
    ('• 動画ピッチ（2分以内）が必須。開発者自身の被害者経験をストーリーとして語る。', '• Video pitch (under 2 min) mandatory. Tell developer\'s personal victim experience as a story.'),
    
    ('<div class="highlight-title">💻 Microsoft AI for Good — 中優先度</div>', '<div class="highlight-title">💻 Microsoft AI for Good — Medium Priority</div>'),
    ('オンラインフォーム経由', 'Via online form'),
    ('• <b>英語申請必須。</b>Microsoft Azure や Copilot との技術連携を示すと有利。', '• <b>English application mandatory.</b> Showing Azure or Copilot integration is advantageous.'),
    ('• 「AI × 社会課題」のインパクトストーリーが重要。技術的詳細より結果（支援人数・防止率）を語る。', '• "AI × Social Issue" impact story is key. Focus on results (people helped, prevention rate) over technical details.'),
    ('• クラウドクレジット（Azure）の提供もあり、インフラコスト削減に直結。', '• Cloud credits (Azure) may be provided, directly reducing infrastructure costs.'),
    ('• パートナー組織（NPO・大学）との共同申請が推奨される。', '• Joint application with partner organizations (NPOs, universities) is recommended.'),
    
    ('<div class="highlight-title">📱 Meta Community Grants — 中優先度</div>', '<div class="highlight-title">📱 Meta Community Grants — Medium Priority</div>'),
    ('オンラインフォーム経由', 'Via online form'),
    ('• <b>英語申請必須。</b>「オンライン安全」「コミュニティ保護」がキーワード。', '• <b>English application mandatory.</b> Keywords: "online safety," "community protection."'),
    ('• 小規模助成（$1万-10万）だが、申請ハードルが低く、初心者に適している。', '• Small grants ($10K-100K) but low application barrier, suitable for beginners.'),
    ('• コミュニティイベント・啓発活動との連携を示すと強い。', '• Strong if linked to community events and awareness campaigns.'),
    ('• Meta のプラットフォーム（Facebook/Instagram）を活用した啓発キャンペーンとの組み合わせを提案。', '• Propose combining with awareness campaigns using Meta platforms (Facebook/Instagram).'),
    
    ('<div class="highlight-title">💡 申請のコツ</div>', '<div class="highlight-title">💡 Application Tips</div>'),
    ('1. <b>同時多投</b>：1つだけでなく、3-5 つの助成金に同時に申請する<br>', '1. <b>Simultaneous Multi-Apply</b>: Apply to 3-5 grants at once, not just one.<br>'),
    ('2. <b>ストーリー化</b>：技術だけでなく、「誰が・どんな被害を・どう救われるか」を語る<br>', '2. <b>Storytelling</b>: Don\'t just talk tech — tell "who, what harm, and how saved."<br>'),
    ('3. <b>数字で語る</b>：623K 国法・724K 判例・17類型犯罪・被害届不受理防止機能——具体的な数字が説得力を生む<br>', '3. <b>Speak with Numbers</b>: 623K laws, 724K precedents, 17 crime types, anti-grafting — concrete numbers build credibility.<br>'),
    ('4. <b>DEMO を添付</b>：3 分動画 + ONE_PAGER.html で、審査員の負担を最小化する<br>', '4. <b>Attach a Demo</b>: 3-min video + ONE_PAGER.html minimizes reviewer burden.<br>'),
    ('5. <b>メール問い合わせを先に</b>：正式申請前に「問い合わせメール」で担当者と接点を作り、ニーズをヒアリングする<br>', '5. <b>Email Inquiry First</b>: Before formal application, make contact via inquiry email to understand needs.<br>'),
    ('6. <b>返信がない場合のフォロー</b>：2週間経過したら丁寧なフォローメールを送る。電話で直接担当者に聞くのも有効。', '6. <b>Follow-up on No Reply</b>: After 2 weeks, send a polite follow-up. Calling the contact directly also works.'),
    
    # Page 5
    ('<!-- PAGE 5: 技術アーキテクチャ -->', '<!-- PAGE 5: Tech Architecture -->'),
    ('<div class="tagline">技術アーキテクチャとデータベース APP 化ガイド</div>', '<div class="tagline">Tech Architecture & Database APP Guide</div>'),
    ('<div class="section-title">5. 技術スタックとベクトルデータベース</div>', '<div class="section-title">5. Tech Stack & Vector Database</div>'),
    
    # Page 6
    ('<!-- PAGE 6: スマホ機能連携 -->', '<!-- PAGE 6: Mobile Integration -->'),
    ('<div class="tagline">スマホ機能連携（GPS・カメラ・マイク・SMS）</div>', '<div class="tagline">Mobile Integration (GPS, Camera, Mic, SMS)</div>'),
]

for old_text, new_text in replacements:
    content = content.replace(old_text, new_text)

with open('LEGALSHIELD_INTRO_EN.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Part 2 translation completed.')
print(f'Total chars: {len(content):,}')

# Check remaining CJK
import re
cjk_chars = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', content)
print(f'Remaining CJK characters: {len(cjk_chars)}')
