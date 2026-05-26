"use strict";

// API base — relative when served via the same nginx vhost (production),
// absolute when served separately (dev). Override with window.API_BASE if needed.
const API_BASE = window.API_BASE || (
  location.port === "8092" ? "http://localhost:8090" : ""
);

const map = L.map("map").setView([35.681, 139.767], 11);
window.map = map;  // exposed for intake.js tab-switch invalidateSize()
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "© OpenStreetMap contributors",
}).addTo(map);

let userMarker = null;
let resultLayer = L.layerGroup().addTo(map);
let userLat = null, userLng = null;

// ─── Geolocation ────────────────────────────────────────────────────
navigator.geolocation.getCurrentPosition(
  pos => {
    userLat = pos.coords.latitude;
    userLng = pos.coords.longitude;
    placeUser(userLat, userLng);
    map.setView([userLat, userLng], 13);
    refreshAll();
  },
  err => {
    document.getElementById("risk-loading").textContent =
      "位置情報を取得できませんでした。地図をクリックして位置を指定してください。";
  },
  { enableHighAccuracy: true, timeout: 10000 }
);

map.on("click", e => {
  userLat = e.latlng.lat;
  userLng = e.latlng.lng;
  placeUser(userLat, userLng);
  refreshAll();
});

document.getElementById("radius").addEventListener("change", refreshSupport);
document.getElementById("org-type").addEventListener("change", refreshSupport);
document.getElementById("rep-submit").addEventListener("click", submitReport);

function placeUser(lat, lng) {
  if (userMarker) userMarker.remove();
  userMarker = L.marker([lat, lng], {
    title: "現在地",
  }).addTo(map).bindPopup("📍 現在地").openPopup();
}

async function refreshAll() {
  await Promise.all([refreshRisk(), refreshSupport()]);
}

async function refreshRisk() {
  if (userLat == null) return;
  const url = `${API_BASE}/api/v1/legalshield/risk-score?lat=${userLat}&lng=${userLng}`;
  document.getElementById("risk-loading").hidden = false;
  document.getElementById("risk-content").hidden = true;
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(await r.text());
    const j = await r.json();
    document.getElementById("risk-count").textContent =
      j.crime_12m_count.toLocaleString("ja-JP") + " 件";
    document.getElementById("risk-pct").textContent =
      j.national_percentile != null
        ? Math.round(j.national_percentile * 100) + " 百分位"
        : "—";
    const badge = document.getElementById("risk-badge");
    badge.textContent = ({
      very_low: "リスク非常に低い",
      low: "リスク低い",
      moderate: "中程度",
      high: "高い",
      very_high: "非常に高い",
      unknown: "データなし",
    })[j.interpretation] || "—";
    badge.className = "badge " + (j.interpretation || "");
    document.getElementById("risk-content").hidden = false;
  } catch (e) {
    document.getElementById("risk-loading").textContent =
      "リスクデータを取得できませんでした (該当データなし可能性)。";
    return;
  } finally {
    document.getElementById("risk-loading").hidden = true;
  }
}

async function refreshSupport() {
  if (userLat == null) return;
  const radius = document.getElementById("radius").value;
  const orgType = document.getElementById("org-type").value;
  const u = new URL(`${API_BASE}/api/v1/legalshield/nearest-support`, location.href);
  u.searchParams.set("lat", userLat);
  u.searchParams.set("lng", userLng);
  u.searchParams.set("radius_km", radius);
  if (orgType) u.searchParams.set("type", orgType);

  resultLayer.clearLayers();
  const list = document.getElementById("result-list");
  list.innerHTML = "<li>読み込み中…</li>";

  try {
    const r = await fetch(u);
    if (!r.ok) throw new Error(await r.text());
    const j = await r.json();
    list.innerHTML = "";
    if (j.results.length === 0) {
      list.innerHTML = "<li class='meta'>該当する支援リソースが見つかりませんでした。検索範囲を広げてください。</li>";
      return;
    }
    for (const o of j.results) {
      const li = document.createElement("li");
      li.innerHTML = `
        <div class="name">${escapeHtml(o.name)}</div>
        <div class="meta">${escapeHtml(o.org_type)} ・ ${(o.distance_m/1000).toFixed(1)} km</div>
        <div class="meta">${escapeHtml(o.address || "")}</div>
      `;
      list.appendChild(li);
      L.marker([o.lat, o.lng])
        .bindPopup(
          `<strong>${escapeHtml(o.name)}</strong><br>` +
          `${escapeHtml(o.org_type)}<br>` +
          `${escapeHtml(o.address || "")}<br>` +
          ((o.contact && o.contact.phone) ? `📞 ${escapeHtml(o.contact.phone)}<br>` : "") +
          (o.source_url ? `<a href="${o.source_url}" target="_blank" rel="noopener">公式サイト</a>` : "")
        )
        .addTo(resultLayer);
    }
  } catch (e) {
    list.innerHTML = `<li class='meta'>取得エラー: ${escapeHtml(String(e))}</li>`;
  }
}

async function submitReport() {
  if (userLat == null) {
    setRepStatus("位置情報が必要です。", "err");
    return;
  }
  const itype = document.getElementById("rep-type").value;
  const desc  = document.getElementById("rep-desc").value;
  setRepStatus("送信中…");
  try {
    const r = await fetch(`${API_BASE}/api/v1/legalshield/incident-report`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        lat: userLat,
        lng: userLng,
        incident_type: itype,
        description: desc,
        anonymous: true,
      }),
    });
    if (!r.ok) throw new Error(await r.text());
    const j = await r.json();
    setRepStatus(`匿名で送信されました (ID: ${j.id.slice(0, 8)}…). 偏移半径: ${j.obfuscation_radius_m[0]}-${j.obfuscation_radius_m[1]} m`, "ok");
    document.getElementById("rep-desc").value = "";
  } catch (e) {
    setRepStatus("送信失敗: " + e, "err");
  }
}

function setRepStatus(msg, cls) {
  const el = document.getElementById("rep-status");
  el.textContent = msg;
  el.className = cls || "";
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[c]);
}
