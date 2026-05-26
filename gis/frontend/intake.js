"use strict";

/* LegalShield intake flow
 * 6-question triage → POST /api/v1/legalshield/intake → tier cards.
 * No framework, no build step — vanilla JS so the static bundle stays light.
 */

const API_BASE_INTAKE = window.API_BASE || (
  location.port === "8092" ? "http://localhost:8090" : ""
);

// ─── client_hash (anonymous, persists per device) ─────────────────────
function getClientHash() {
  const key = "legalshield_client_hash";
  let h = localStorage.getItem(key);
  if (!h) {
    h = "c_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    try { localStorage.setItem(key, h); } catch (_) { /* private mode */ }
  }
  return h;
}

// ─── tab switching ────────────────────────────────────────────────────
document.querySelectorAll("#tabs .tab").forEach(t => {
  t.addEventListener("click", () => showTab(t.dataset.tab));
});

function showTab(name) {
  document.querySelectorAll("#tabs .tab").forEach(t =>
    t.classList.toggle("is-active", t.dataset.tab === name)
  );
  document.querySelectorAll(".tab-panel").forEach(p =>
    p.classList.toggle("is-active", p.id === `tab-${name}`)
  );
  // Leaflet needs an explicit redraw when map panel becomes visible
  if (name === "map" && window.map && typeof window.map.invalidateSize === "function") {
    setTimeout(() => window.map.invalidateSize(), 50);
  }
}

// ─── 6Q state machine ─────────────────────────────────────────────────
const answers = {
  immediate_danger: null,
  bucket: null,
  duration: null,
  free_text: null,
  prior_consult: null,
  want: null,
};

document.querySelectorAll(".opt[data-q]").forEach(btn => {
  btn.addEventListener("click", () => handleOpt(btn));
});

document.getElementById("btn-emergency").addEventListener("click", () => {
  answers.immediate_danger = true;
  answers.bucket = "interpersonal_violence"; // safest default for unrouted emergency
  answers.duration = "today";
  answers.want = "act_with_me";
  submit();
});

document.getElementById("btn-restart").addEventListener("click", () => {
  Object.keys(answers).forEach(k => answers[k] = null);
  document.querySelectorAll(".q").forEach((q, i) => {
    q.hidden = (i !== 0);
    q.classList.toggle("is-active", i === 0);
  });
  document.querySelectorAll(".opt").forEach(b => b.classList.remove("is-selected"));
  document.getElementById("q4-text").value = "";
  document.getElementById("intake-form").hidden = false;
  document.getElementById("intake-result").hidden = true;
  updateProgress(1);
});

document.getElementById("btn-show-map").addEventListener("click", () => showTab("map"));

function handleOpt(btn) {
  const q = parseInt(btn.dataset.q, 10);
  const v = btn.dataset.val;

  // record answer
  if (q === 1) {
    answers.immediate_danger = (v === "yes");
    if (v === "yes") { submit(); return; }   // emergency: skip to submit
  } else if (q === 2) {
    answers.bucket = v;
  } else if (q === 3) {
    answers.duration = v;
  } else if (q === 4) {
    answers.free_text = (v === "next")
      ? document.getElementById("q4-text").value.trim() || null
      : null;
  } else if (q === 5) {
    answers.prior_consult = v;
  } else if (q === 6) {
    answers.want = v;
    submit();
    return;
  }

  // visual select state
  btn.parentElement.querySelectorAll(".opt").forEach(b => b.classList.remove("is-selected"));
  btn.classList.add("is-selected");

  // advance to next question
  const next = q + 1;
  document.querySelectorAll(".q").forEach(qd => {
    const idx = parseInt(qd.dataset.q, 10);
    qd.hidden = (idx !== next);
    qd.classList.toggle("is-active", idx === next);
  });
  updateProgress(next);
}

function updateProgress(current) {
  document.querySelectorAll("#intake-progress .step").forEach((el, i) => {
    el.classList.toggle("is-current", (i + 1) === current);
    el.classList.toggle("is-done", (i + 1) < current);
  });
}

// ─── submit ───────────────────────────────────────────────────────────
async function submit() {
  const body = {
    immediate_danger: !!answers.immediate_danger,
    bucket: answers.bucket || "other",
    duration: answers.duration || "today",
    free_text: answers.free_text,
    prior_consult: answers.prior_consult,
    want: answers.want,
    language: "ja",
  };

  document.getElementById("intake-form").hidden = true;
  const result = document.getElementById("intake-result");
  result.hidden = false;
  document.getElementById("tier-cards").innerHTML =
    '<div class="loading">あなたに合った相談先を探しています...</div>';

  try {
    const r = await fetch(`${API_BASE_INTAKE}/api/v1/legalshield/intake`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "X-Client-Hash": getClientHash(),
      },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
    const j = await r.json();
    renderResult(j);
  } catch (e) {
    document.getElementById("tier-cards").innerHTML =
      `<div class="err">送信エラー: ${escape(String(e))}</div>`;
  }
}

// ─── render recommendations ───────────────────────────────────────────
function renderResult(j) {
  // Detection summary
  document.getElementById("det-cat").textContent = j.detection.category_name_ja || j.detection.category;
  document.getElementById("det-conf").textContent = Math.round(j.detection.confidence * 100);

  // Emergency banner
  const ebanner = document.getElementById("emergency-banner");
  const eMsg = document.getElementById("emergency-msg");
  const eTel = document.getElementById("emergency-tel");
  if (j.emergency && j.emergency.is_emergency) {
    ebanner.hidden = false;
    eMsg.textContent = j.emergency.message_ja || "ご無事ですか。下の番号にすぐ電話してください。";
    const tel = j.emergency.urgent_hotline;
    if (tel) {
      eTel.href = telHref(tel);
      eTel.textContent = `📞 ${tel} に電話する`;
    } else {
      eTel.hidden = true;
    }
  } else {
    ebanner.hidden = true;
  }

  // Tier cards
  const wrap = document.getElementById("tier-cards");
  wrap.innerHTML = "";
  for (const tier of j.recommendations.tiers) {
    const sec = document.createElement("section");
    sec.className = `tier-card tier-${tier.tier}`;
    sec.innerHTML = `
      <div class="tier-header">
        <span class="tier-badge">Tier ${tier.tier}</span>
        <span class="tier-name">${tierName(tier.tier)}</span>
      </div>
    `;
    for (const route of tier.routes) {
      const card = document.createElement("article");
      card.className = "route-card score-" + scoreClass(route.score);
      const phones = extractPhones(route.org_name_pattern + " " + (route.notes_ja || ""));
      card.innerHTML = `
        <div class="route-head">
          <div class="org-name">${escape(route.org_name_pattern || "")}</div>
          <div class="org-kind">${kindLabel(route.org_kind)} · score ${route.score}</div>
        </div>
        ${phones.length ? `<div class="route-tels">${phones.map(p =>
          `<a class="dial-btn" href="${telHref(p)}">📞 ${escape(p)}</a>`
        ).join("")}</div>` : ""}
        <details class="route-detail">
          <summary>言い方・持ち物・期待される対応</summary>
          ${route.what_to_say_ja ? `<p class="what-to-say">🗣️ <strong>言い方の例：</strong> ${escape(route.what_to_say_ja)}</p>` : ""}
          ${route.documents_needed_ja && route.documents_needed_ja.length
            ? `<div class="docs"><strong>📋 持ち物：</strong><ul>${
              route.documents_needed_ja.map(d => `<li>${escape(d)}</li>`).join("")
            }</ul></div>` : ""}
          ${route.expected_outcome_ja ? `<p class="expected">✅ <strong>期待される対応：</strong> ${escape(route.expected_outcome_ja)}</p>` : ""}
          ${route.next_tier_if_ja ? `<p class="next-tier">↗️ <strong>次の段階へ：</strong> ${escape(route.next_tier_if_ja)}</p>` : ""}
          ${route.notes_ja ? `<p class="notes">💡 ${escape(route.notes_ja)}</p>` : ""}
        </details>
      `;
      sec.appendChild(card);
    }
    wrap.appendChild(sec);
  }
}

// ─── utilities ────────────────────────────────────────────────────────
function tierName(n) {
  return ({
    1: "緊急ホットライン",
    2: "公的相談窓口",
    3: "専門 NPO・支援団体",
    4: "法的対応（弁護士・ADR）",
    5: "司法手続・公共訴訟",
  })[n] || "";
}
function kindLabel(k) {
  return ({
    hotline:      "📞 ホットライン",
    admin_center: "🏛️ 公的窓口",
    police:       "🚓 警察",
    npo:          "🤝 NPO・支援団体",
    bar_assoc:    "⚖️ 弁護士会",
    court:        "🏛️ 裁判所・ADR",
    shelter:      "🏠 シェルター",
  })[k] || k;
}
function scoreClass(s) {
  if (s >= 1.0) return "high";
  if (s >= 0.7) return "mid";
  return "low";
}
function extractPhones(s) {
  if (!s) return [];
  // matches: #8008, #189, 110, 188, 0120-..., 03-...-..., 0570-..., etc.
  const re = /(#\d{3,4}|\b0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4}\b|\b1\d{2}\b)/g;
  const found = new Set();
  let m;
  while ((m = re.exec(s)) !== null) found.add(m[1]);
  return [...found];
}
function telHref(phone) {
  const p = String(phone).trim();
  // # needs URI encoding for tel:
  if (p.startsWith("#")) return "tel:" + encodeURIComponent(p);
  return "tel:" + p.replace(/[-\s]/g, "");
}
function escape(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[c]);
}
