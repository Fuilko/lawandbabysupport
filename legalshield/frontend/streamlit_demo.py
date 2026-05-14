"""LegalShield Streamlit Demo — Anti-Grafting Edition.

Run:   streamlit run legalshield/frontend/streamlit_demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hashlib
import json
from datetime import datetime, timezone

import streamlit as st

st.set_page_config(
    page_title="LegalShield — 被害者支援システム",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom CSS
css = """
<style>
  .block-container { max-width: 480px; padding: 1rem; }
  .emergency-btn {
    width:100%; padding:1.5rem; border-radius:1rem; border:none;
    background:linear-gradient(135deg,#ff4757,#c0392b); color:#fff;
    font-size:1.5rem; font-weight:700; text-align:center; cursor:pointer;
    box-shadow: 0 0 30px rgba(255,71,87,0.3);
  }
  .emergency-btn:active { transform: scale(0.97); }
  .role-card {
    background: #121a33; border: 1px solid #243260; border-radius: 10px;
    padding: 12px; margin-bottom: 8px; display:flex; gap:10px; align-items:center;
  }
  .role-icon { width:40px; height:40px; border-radius:50%; display:flex;
    align-items:center; justify-content:center; font-size:20px; flex-shrink:0;
  }
  .role-title { font-weight:700; color:#fff; font-size:14px; }
  .role-desc { font-size:12px; color:#9aa7d0; }
  .progress-bar { width:100%; height:4px; background:#172246; border-radius:2px; margin:16px 0; }
  .progress-fill { height:100%; background:#7cf0c2; border-radius:2px; transition:width .3s; }
  .option-btn { width:100%; text-align:left; padding:14px; border-radius:10px;
    border:1px solid #243260; background:#121a33; color:#e6ecff;
    margin-bottom:8px; cursor:pointer;
  }
  .option-btn:hover { border-color:#7cf0c2; }
  .stButton > button { width:100%; border-radius:10px; }
  .check-item { padding:8px; background:#0f1a36; border-radius:6px; margin-bottom:6px; font-size:13px; }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# Session state init
if "screen" not in st.session_state:
    st.session_state.screen = "welcome"
if "triage" not in st.session_state:
    st.session_state.triage = {}
if "scenario" not in st.session_state:
    st.session_state.scenario = "DV"


def set_screen(name):
    st.session_state.screen = name


def render_welcome():
    st.markdown('<div style="text-align:center; margin-bottom:16px"><div style="font-size:24px; font-weight:700; color:#7cf0c2">LegalShield</div><div style="font-size:13px; color:#9aa7d0">誰も1人にはしない</div></div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; margin-bottom:20px; font-size:12px; color:#5ad19a">● 現在の環境は安全ですか？</div>', unsafe_allow_html=True)

    if st.button("🚨 助けて\n\n長押し2秒で緊急モード", key="emergency", use_container_width=True):
        set_screen("emergency")
        st.rerun()

    st.divider()

    for emoji, title, desc, target in [
        ("💬", "相談を始める", "AIが状況を整理して支援します", "triage_1"),
        ("📁", "証拠を保存", "写真・録音・書類を安全に保管", "evidence"),
    ]:
        if st.button(f"**{title}**\n\n{desc}", key=target, use_container_width=True):
            set_screen(target)
            st.rerun()

    st.caption("緊急時は直接 110 / 119 にご連絡ください。本アプリは補助ツールです。")


def render_emergency():
    st.markdown("<div style='text-align:center'><div style='font-size:16px;font-weight:700;color:#ff6b6b'>緊急モード</div><div style='font-size:13px;color:#9aa7d0'>10秒後に支援メッセージを送信します</div></div>", unsafe_allow_html=True)

    countdown = st.empty()
    if st.button("キャンセル", key="cancel_emergency", type="secondary"):
        set_screen("welcome")
        st.rerun()

    for i in range(10, -1, -1):
        countdown.markdown(f"<div style='text-align:center'><div style='font-size:72px;font-weight:700;color:#ff4757'>{i}</div></div>", unsafe_allow_html=True)
        import time
        time.sleep(0.3)  # demo speed

    countdown.markdown("<div style='text-align:center'><div style='font-size:72px;font-weight:700;color:#7cf0c2'>✓</div><div style='color:#7cf0c2;font-weight:600'>支援メッセージを送信しました</div></div>", unsafe_allow_html=True)
    st.info("""
**送信先:**
- 設定された緊急連絡先（山田さん）
- 最寄りのDV支援センター（○○市）
- 法テラス相談窓口

GPS位置情報と状況を含むメッセージをサイレント（無音）で送信しました。
    """)
    if st.button("ホームに戻る", key="emergency_home"):
        set_screen("welcome")
        st.rerun()


def render_triage_1():
    st.markdown('<div class="progress-bar"><div class="progress-fill" style="width:20%"></div></div>', unsafe_allow_html=True)
    st.markdown("<div style='font-size:18px;font-weight:600;text-align:center;margin-bottom:16px'>今、あなたは安全な場所にいますか？</div>", unsafe_allow_html=True)

    for val, label in [("safe", "はい、安全です"), ("unsafe", "いいえ、不安です"), ("unknown", "わからない")]:
        if st.button(label, key=f"t1_{val}", use_container_width=True):
            st.session_state.triage["safety"] = val
            set_screen("triage_2")
            st.rerun()

    if st.button("戻る", key="t1_back"):
        set_screen("welcome")
        st.rerun()


def render_triage_2():
    st.markdown('<div class="progress-bar"><div class="progress-fill" style="width:40%"></div></div>', unsafe_allow_html=True)
    st.markdown("<div style='font-size:18px;font-weight:600;text-align:center;margin-bottom:16px'>どんなことが起きていますか？<br/><span style='font-size:13px;color:#9aa7d0'>複数選択可</span></div>", unsafe_allow_html=True)

    selected = st.session_state.triage.get("issues", [])
    options = ["violence", "sexual", "money", "work", "child", "other"]
    labels = ["暴力を受けている", "性的な被害を受けた", "お金を騙し取られた", "職場で困っている", "子どもが被害を受けている", "その他"]

    for opt, lab in zip(options, labels):
        checked = opt in selected
        if st.checkbox(lab, value=checked, key=f"t2_{opt}"):
            if opt not in selected:
                selected.append(opt)
        else:
            if opt in selected:
                selected.remove(opt)
    st.session_state.triage["issues"] = selected

    c1, c2 = st.columns(2)
    with c1:
        if st.button("戻る", key="t2_back"):
            set_screen("triage_1")
            st.rerun()
    with c2:
        if st.button("次へ", key="t2_next", disabled=len(selected) == 0):
            set_screen("triage_3")
            st.rerun()


def render_triage_3():
    st.markdown('<div class="progress-bar"><div class="progress-fill" style="width:60%"></div></div>', unsafe_allow_html=True)
    st.markdown("<div style='font-size:18px;font-weight:600;text-align:center;margin-bottom:16px'>今、私たちに何を手伝ってほしいですか？</div>", unsafe_allow_html=True)

    for val, label in [
        ("record", "状況を整理して記録したい"),
        ("law", "法律のこと・自分の権利を知りたい"),
        ("contact", "専門家・相談窓口につながりたい"),
        ("evidence", "証拠を安全に保存したい"),
    ]:
        if st.button(label, key=f"t3_{val}", use_container_width=True):
            st.session_state.triage["goal"] = val
            set_screen("consent")
            st.rerun()

    if st.button("戻る", key="t3_back"):
        set_screen("triage_2")
        st.rerun()


def render_consent():
    st.markdown('<div class="progress-bar"><div class="progress-fill" style="width:80%"></div></div>', unsafe_allow_html=True)
    st.markdown("<div style='font-size:18px;font-weight:600;text-align:center;margin-bottom:16px'>利用規約と同意事項</div>", unsafe_allow_html=True)

    with st.expander("⚠️ 重要な免責事項", expanded=True):
        st.warning("""
LegalShield は「情報整理・補助ツール」です。

• 緊急通報の100%即時性を保証しません
• GPS位置情報の完全正確性を保証しません
• AI判定の100%正確性を保証しません
• 生命・身体の危険がある場合、直接 110 / 119 にご連絡ください

当社は、通信回線の混雑・途切れ、端末の電池切れ・故障、AIの誤判定、第三者の対応遅延による損害について、一切の責任を負いません。
        """)

    c1 = st.checkbox("GPS位置情報の利用に同意\n\n最寄り施設検索・緊急時位置送信用", key="c_gps")
    c2 = st.checkbox("マイク・カメラの利用に同意\n\n証拠収集・通話録音用", key="c_mic")
    c3 = st.checkbox("緊急連絡先への自動送信に同意\n\n10秒カウントダウン後の自動SMS送信", key="c_emergency")
    c4 = st.checkbox("利用規約・免責事項に同意します\n\n本アプリは110番の代替ではありません", key="c_terms")

    c1b, c2b = st.columns(2)
    with c1b:
        if st.button("戻る", key="consent_back"):
            set_screen("triage_3")
            st.rerun()
    with c2b:
        if st.button("同意して始める", key="consent_next", disabled=not (c1 and c2 and c3 and c4)):
            set_screen("result")
            st.rerun()


def render_result():
    # Determine scenario
    issues = st.session_state.triage.get("issues", [])
    if "violence" in issues:
        scenario = "DV"
    elif "sexual" in issues:
        scenario = "性暴力"
    elif "money" in issues:
        scenario = "消費者被害"
    elif "work" in issues:
        scenario = "職場"
    elif "child" in issues:
        scenario = "児童虐待"
    else:
        scenario = "DV"
    st.session_state.scenario = scenario

    st.markdown("<div style='text-align:center;margin-bottom:16px'><div style='font-size:20px;font-weight:700'>あなたの行動プラン</div></div>", unsafe_allow_html=True)

    # 5 AI roles
    for emoji, color, title, desc in [
        ("🚨", "#ff6b6b", "緊急対応", "#8898（DV相談）\n警察 110（必要に応じて）"),
        ("📁", "#ffd166", "証拠保全", "診断書・写真・LINEのスクリーンショット"),
        ("⚖️", "#7cf0c2", "法律分析", "配偶者暴力防止法・刑法204条（傷害罪）"),
        ("🧭", "#7cf0c2", "戦略シミュレーション", "保護命令申請（推奨）+ 民事損害賠償"),
        ("🗺️", "#ffd166", "専家紹介", "東京弁護士会・法テラス東京・○○シェルター"),
    ]:
        st.markdown(f"""
        <div class="role-card" style="border-color:{color}">
            <div class="role-icon" style="background:#1a2330">{emoji}</div>
            <div>
                <div class="role-title">{title}</div>
                <div class="role-desc">{desc.replace(chr(10), '<br>')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown("<div style='font-size:16px;font-weight:700;color:#7cf0c2;margin-bottom:10px'>🛡️ 防吃案機能 — 警察への備え</div>", unsafe_allow_html=True)

    if st.button("📄 警察訪問用スクリプトを生成", key="gen_police_script", use_container_width=True):
        set_screen("anti_grafting")
        st.rerun()

    if st.button("💾 レポートを保存して終了", key="save_report", use_container_width=True):
        st.success("レポートを保存しました。次回起動時から続けられます。")
        set_screen("welcome")
        st.rerun()


def render_anti_grafting():
    st.markdown("<div style='font-size:20px;font-weight:700;color:#7cf0c2;margin-bottom:10px'>🛡️ 防吃案 — 警察訪問ガイド</div>", unsafe_allow_html=True)

    scenario = st.session_state.get("scenario", "DV")
    st.info(f"シナリオ: **{scenario}**")

    # Load the anti-grafting module logic inline
    scripts = {
        "DV": {
            "title": "配偶者暴力被害届提出",
            "legal_basis": ["刑法第204条（傷害罪）", "刑法第222条（脅迫罪）", "配偶者暴力防止及び被害者保護法第3条（保護命令）"],
            "demand": "被害届の受理と発行を求めます",
            "if_refused": {
                "『これは民事です』": "刑法204条・222条に該当する刑事事件です。『民事不介入』ではなく、『犯罪の告訴』です。受理拒否は職務怠慢になります。",
                "『被害届は必要ありません』": "被害届受理番号が発行されない場合、『被害届不受理通知書』（告訴不受理通知書）の交付を求めます。これは刑事訴訟法第230条に基づく権利です。",
                "『証拠が不十分です』": "被害届の受理には証拠の充実性は不要です（捜査は受理後に行われます）。診断書・写真・LINEスクリーンショットを添付しています。",
                "『相談で記録します』": "『相談』ではなく『被害届』として正式受理してください。相談記録では捜査は開始されません。",
            },
            "docs_required": ["身分証明書", "診断書（医療機関発行）", "受傷写真（タイムスタンプ付き）", "脅迫メッセージスクリーンショット", "LegalShield報告書"],
        },
        "性暴力": {
            "title": "性犯罪被害届提出",
            "legal_basis": ["刑法第176条（強制わいせつ罪）", "刑法第177条（強制性交等罪）", "刑法第178条の2（不同意性交等罪）"],
            "demand": "被害届の受理と発行を求めます",
            "if_refused": {
                "『合意があったのでは？』": "『同意なし』です。意識不明・抵抗不能の状態でした。法医学的検査を受けています。DNA証拠を保全中です。",
                "『泥酔しただけでは？』": "『不同意性交等罪』は、被害者の同意がないことで成立します。泥酔による抵抗不能状態は、明確な構成要件に該当します。",
                "『被害届は不要、相談で十分』": "被害届受理番号を発行してください。不受理の場合は『被害届不受理通知書』の交付を求めます。",
            },
            "docs_required": ["身分証明書", "法医学的検査結果（指定病院）", "現場写真・位置情報", "犯人との通訊記録", "LegalShield報告書"],
        },
    }
    script = scripts.get(scenario, scripts["DV"])

    st.markdown(f"<div style='font-size:14px;font-weight:700;margin-bottom:8px'>{script['title']}</div>", unsafe_allow_html=True)

    st.markdown("**法條根拠:**")
    for law in script["legal_basis"]:
        st.markdown(f"- {law}")

    st.markdown(f"**あなたの主張:**\n> 「{script['demand']}」")

    st.markdown("**警察の言い訳とあなたの反論:**")
    for excuse, counter in script["if_refused"].items():
        with st.expander(f"警察: {excuse}"):
            st.success(f"あなた: {counter}")

    st.markdown("**持参書類チェックリスト:**")
    for doc in script["docs_required"]:
        st.checkbox(doc, key=f"doc_{doc}")

    # Immutable hash generation
    ts = datetime.now(timezone.utc).isoformat()
    content = json.dumps(script, ensure_ascii=False, sort_keys=True)
    h = hashlib.sha256(content.encode()).hexdigest()

    st.markdown(f"<div style='font-size:11px;color:#6a7ab0;margin-top:10px'>不変ハッシュ: {h[:32]}...</div>", unsafe_allow_html=True)

    if st.button("📧 メールで自分に送信（バックアップ）", key="email_backup"):
        st.success("バックアップメールを送信しました！")

    st.divider()
    st.markdown("<div style='font-size:16px;font-weight:700;color:#ffd166;margin-bottom:10px'>🔥 もし受理されない場合</div>", unsafe_allow_html=True)

    for title, body in [
        ("1. 都道府県公安委員会へ申立て", "警察の監督機関です。不受理の理由を記録し、職務怠慢として申立てます。"),
        ("2. 地方検察庁検察審査会へ申立て", "検察官に直接告訴を求めます。整理済みの証拠パッケージを添付します。"),
        ("3. 警察庁へ苦情申立て", "全国レベルでの警察職務違反として記録されます。"),
    ]:
        with st.expander(title):
            st.info(body)

    if st.button("戻る", key="ag_back"):
        set_screen("result")
        st.rerun()


def render_evidence():
    st.markdown("<div style='text-align:center;margin-bottom:16px'><div style='font-size:20px;font-weight:700'>証拠を安全に保存</div><div style='font-size:13px;color:#9aa7d0'>写真・録音・書類をアップロード</div></div>", unsafe_allow_html=True)

    for emoji, title, desc in [
        ("📷", "写真を撮る", "タイムスタンプ・GPS付きで保存"),
        ("🎙️", "録音をする", "音声をテキスト化して記録"),
        ("📄", "ファイルをアップロード", "診断書・領収書・スクリーンショット"),
    ]:
        st.markdown(f"""
        <div class="role-card">
            <div class="role-icon" style="background:#1a2330">{emoji}</div>
            <div>
                <div class="role-title">{title}</div>
                <div class="role-desc">{desc}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if st.button("戻る", key="evidence_back"):
        set_screen("welcome")
        st.rerun()


# Main router
screen = st.session_state.screen

if screen == "welcome":
    render_welcome()
elif screen == "emergency":
    render_emergency()
elif screen == "triage_1":
    render_triage_1()
elif screen == "triage_2":
    render_triage_2()
elif screen == "triage_3":
    render_triage_3()
elif screen == "consent":
    render_consent()
elif screen == "result":
    render_result()
elif screen == "anti_grafting":
    render_anti_grafting()
elif screen == "evidence":
    render_evidence()
else:
    render_welcome()
