"""KI Enterprise Dashboard - web arayuzu (Phase 9 + 2026-07-16 Chief-bazli
yeniden yazim).

Tek sayfa, sunucu-tarafinda render edilmeyen, tarayicida ayni-origin API
uclarina (bkz. main.py) fetch() ile baglanan statik bir HTML/JS sayfasi.

2026-07-16 degisikligi: sayfa artik DASHBOARD_UI_TOKEN'i GOMMUYOR. Once bir
login ekrani gosterilir (POST /api/v1/dashboard/auth/login), basarili giriste
donen token SADECE tarayicinin sessionStorage'inda tutulur - sayfa kaynagini
goruntuleyen biri artik token'i dogrudan goremez (eskiden goruyordu, bkz. eski
docstring). Traefik'teki ki-dashboard-auth BasicAuth katmani
(infrastructure/traefik/dynamic/dashboard.yml) bagimsiz/degismeden kalir, bu
SADECE ek bir uygulama-ici katman (ozellikle Traefik'i atlayan dogrudan :5009
erisiminde onemli).
"""


def render_dashboard_html() -> str:
    return """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KI Enterprise Dashboard</title>
<style>
  :root {
    --bg: #0b0e14; --panel: #131722; --panel-2: #0e131d; --border: #232838; --text: #e6e9ef;
    --muted: #8b93a7; --ok: #3ecf8e; --bad: #ef5350; --warn: #f0b429; --accent: #5b8def; --accent-2: #8b6bef;
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,Segoe UI,Roboto,sans-serif; }
  button { font-family:inherit; }
  input, select, textarea { font-family:inherit; }

  /* ---------- Login ---------- */
  #login-view { min-height:100vh; display:flex; align-items:center; justify-content:center; padding:20px; }
  .login-card { width:100%; max-width:360px; background:var(--panel); border:1px solid var(--border); border-radius:14px; padding:32px 28px; box-shadow:0 20px 60px rgba(0,0,0,0.4); }
  .login-card h1 { font-size:17px; margin:0 0 4px; }
  .login-card .sub { color:var(--muted); font-size:12px; margin:0 0 24px; }
  .login-field { margin-bottom:14px; }
  .login-field label { display:block; font-size:11px; color:var(--muted); margin-bottom:6px; text-transform:uppercase; letter-spacing:0.04em; }
  .login-field input { width:100%; background:var(--panel-2); border:1px solid var(--border); color:var(--text); border-radius:8px; padding:10px 12px; font-size:14px; }
  .login-field input:focus { outline:none; border-color:var(--accent); }
  #login-btn { width:100%; background:var(--accent); color:#fff; border:none; padding:11px; border-radius:8px; cursor:pointer; font-size:14px; font-weight:600; margin-top:6px; }
  #login-btn:hover { opacity:0.9; }
  #login-btn:disabled { opacity:0.5; cursor:default; }
  #login-error { color:var(--bad); font-size:12px; margin-top:12px; min-height:14px; }

  /* ---------- App shell ---------- */
  #app-view { display:none; }
  header { padding:16px 28px; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; }
  header h1 { font-size:17px; margin:0; font-weight:600; }
  header .sub { color:var(--muted); font-size:12px; margin-top:2px; }
  .header-actions { display:flex; gap:10px; align-items:center; }
  .btn { background:var(--accent); color:#fff; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; font-size:13px; }
  .btn:hover { opacity:0.85; }
  .btn.secondary { background:transparent; border:1px solid var(--border); color:var(--muted); }

  nav#tabs { display:flex; gap:4px; padding:0 28px; border-bottom:1px solid var(--border); overflow-x:auto; background:var(--panel-2); }
  nav#tabs button { background:none; border:none; color:var(--muted); padding:12px 16px; font-size:13px; cursor:pointer; white-space:nowrap; border-bottom:2px solid transparent; }
  nav#tabs button:hover { color:var(--text); }
  nav#tabs button.active { color:var(--text); border-bottom-color:var(--accent); font-weight:600; }

  main { padding:24px 28px; }
  .tab-panel { display:none; }
  .tab-panel.active { display:block; }

  .section-title { font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:0.05em; margin:0 0 12px; }
  .kpi-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:14px; margin-bottom:28px; }
  .kpi-tile { background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:16px; position:relative; }
  .kpi-tile .kpi-label { font-size:12px; color:var(--muted); margin-bottom:8px; min-height:32px; }
  .kpi-tile .kpi-value { font-size:22px; font-weight:700; }
  .kpi-tile .kpi-value.empty { font-size:13px; font-weight:400; color:var(--muted); font-style:italic; }
  .kpi-badge { position:absolute; top:12px; right:12px; font-size:9px; padding:2px 6px; border-radius:8px; text-transform:uppercase; letter-spacing:0.03em; font-weight:600; }
  .kpi-badge.auto { background:rgba(62,207,142,0.15); color:var(--ok); }
  .kpi-badge.manual { background:rgba(91,141,239,0.15); color:var(--accent); }
  .kpi-badge.missing { background:rgba(139,147,167,0.15); color:var(--muted); }
  .kpi-note { font-size:10px; color:var(--muted); margin-top:8px; line-height:1.4; }
  .kpi-fill-btn { margin-top:10px; background:none; border:1px solid var(--border); color:var(--muted); padding:4px 10px; border-radius:6px; font-size:11px; cursor:pointer; }
  .kpi-fill-btn:hover { color:var(--text); border-color:var(--accent); }

  .card { background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:18px; margin-bottom:20px; }
  .card h2 { font-size:14px; margin:0 0 14px; color:var(--muted); text-transform:uppercase; letter-spacing:0.05em; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  table th { text-align:left; color:var(--muted); font-weight:500; padding:6px 4px; border-bottom:1px solid var(--border); }
  table td { padding:6px 4px; border-bottom:1px solid var(--border); }
  .loading { color:var(--muted); font-size:13px; }
  .err { color:var(--bad); font-size:12px; margin-top:8px; }
  .badge { display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; }
  .badge.ok { background:rgba(62,207,142,0.15); color:var(--ok); }
  .badge.degraded { background:rgba(240,180,41,0.15); color:var(--warn); }
  .badge.unreachable { background:rgba(239,83,80,0.15); color:var(--bad); }
  .stat-row { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:12px; }
  .stat { flex:1; min-width:80px; }
  .stat .n { font-size:26px; font-weight:700; }
  .stat .l { font-size:11px; color:var(--muted); margin-top:2px; }

  .metric-form { display:flex; flex-wrap:wrap; gap:10px; align-items:flex-start; margin-top:6px; }
  .metric-form select, .metric-form input {
    background:var(--panel-2); border:1px solid var(--border); color:var(--text); border-radius:6px; padding:8px 10px; font-size:13px;
  }
  .metric-form select { flex:1; min-width:200px; }
  .metric-form input[type=text], .metric-form input[type=number] { flex:1; min-width:120px; }
  .metric-form input[type=password] { flex:1; min-width:180px; }
  .metric-form button { background:var(--accent-2); color:#fff; border:none; padding:9px 16px; border-radius:6px; cursor:pointer; font-size:13px; white-space:nowrap; }
  .metric-form button:hover { opacity:0.85; }
  .metric-result { font-size:12px; margin-top:8px; white-space:pre-wrap; }
  .hint { color:var(--muted); font-size:11px; margin-top:6px; }

  .dispatch-form { display:flex; flex-wrap:wrap; gap:10px; align-items:flex-start; }
  .dispatch-form select, .dispatch-form input, .dispatch-form textarea {
    background:var(--panel-2); border:1px solid var(--border); color:var(--text); border-radius:6px; padding:8px 10px; font-size:13px; font-family:inherit;
  }
  .dispatch-form textarea { flex:2; min-width:260px; min-height:60px; resize:vertical; }
  .dispatch-form select { flex:1; min-width:180px; }
  .dispatch-form input[type=text] { flex:1; min-width:140px; }
  .dispatch-form input[type=password] { flex:1; min-width:180px; }
  .dispatch-form button { background:var(--accent); color:#fff; border:none; padding:9px 18px; border-radius:6px; cursor:pointer; font-size:13px; white-space:nowrap; }
  .dispatch-form button:hover { opacity:0.85; }
  .dispatch-result { margin-top:10px; font-size:12px; white-space:pre-wrap; }

  /* ---------- Chat Odasi ---------- */
  .room-wrap { display:flex; gap:20px; align-items:flex-start; }
  .room-participants { width:200px; flex-shrink:0; background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:14px; }
  .room-participants h2 { font-size:12px; margin:0 0 10px; color:var(--muted); text-transform:uppercase; letter-spacing:0.05em; }
  .room-chief-toggle { display:flex; align-items:center; gap:8px; padding:6px 0; font-size:13px; }
  .room-chief-toggle input { accent-color:var(--accent); }
  .room-chief-toggle.ceo-fixed { color:var(--muted); }
  .room-main { flex:1; min-width:0; display:flex; flex-direction:column; background:var(--panel); border:1px solid var(--border); border-radius:10px; overflow:hidden; }
  .room-messages { height:60vh; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:12px; }
  .room-msg { max-width:78%; padding:10px 14px; border-radius:12px; font-size:13px; line-height:1.5; white-space:pre-wrap; }
  .room-msg .room-msg-speaker { font-size:10px; color:var(--muted); margin-bottom:4px; text-transform:uppercase; letter-spacing:0.03em; }
  .room-msg.role-user { align-self:flex-end; background:var(--accent); color:#fff; border-bottom-right-radius:2px; }
  .room-msg.role-user .room-msg-speaker { color:rgba(255,255,255,0.75); }
  .room-msg.role-ceo { align-self:flex-start; background:var(--panel-2); border:1px solid var(--border); border-bottom-left-radius:2px; }
  .room-msg.role-chief { align-self:flex-start; background:rgba(139,107,239,0.12); border:1px solid var(--border); border-bottom-left-radius:2px; }
  .room-msg.role-ceo.report { border-color:var(--ok); }
  .room-msg-dispatch { margin-top:6px; font-size:11px; color:var(--ok); }
  .room-input-row { display:flex; gap:10px; padding:14px; border-top:1px solid var(--border); }
  .room-input-row textarea { flex:1; background:var(--panel-2); border:1px solid var(--border); color:var(--text); border-radius:8px; padding:10px 12px; font-size:13px; font-family:inherit; resize:none; min-height:44px; max-height:120px; }
  .room-input-row button { background:var(--accent); color:#fff; border:none; padding:0 20px; border-radius:8px; cursor:pointer; font-size:13px; }
  .room-input-row button:hover { opacity:0.85; }
  .room-input-row button:disabled { opacity:0.5; cursor:default; }

  /* ---------- Integrations ---------- */
  .integ-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:16px; margin-bottom:20px; }
  .integ-card h2 { display:flex; align-items:center; justify-content:space-between; }
  .integ-card .integ-count { font-size:11px; color:var(--muted); font-weight:400; text-transform:none; }
  .integ-item { display:flex; align-items:center; justify-content:space-between; padding:8px 0; border-bottom:1px solid var(--border); font-size:12px; gap:8px; }
  .integ-item:last-child { border-bottom:none; }
  .integ-item .integ-name { font-weight:600; }
  .integ-item .integ-identity { color:var(--muted); font-size:11px; }
  .integ-item .integ-actions { display:flex; gap:6px; flex-shrink:0; }
  .integ-item .integ-actions button { background:none; border:1px solid var(--border); color:var(--muted); padding:3px 8px; border-radius:5px; font-size:10px; cursor:pointer; }
  .integ-item .integ-actions button:hover { color:var(--text); border-color:var(--accent); }
  .integ-form { display:flex; flex-wrap:wrap; gap:10px; align-items:flex-start; }
  .integ-form input, .integ-form select { background:var(--panel-2); border:1px solid var(--border); color:var(--text); border-radius:6px; padding:8px 10px; font-size:13px; flex:1; min-width:150px; }
  .integ-form button { background:var(--accent); color:#fff; border:none; padding:9px 16px; border-radius:6px; cursor:pointer; font-size:13px; white-space:nowrap; }
</style>
</head>
<body>

<div id="login-view">
  <div class="login-card">
    <h1>KI Enterprise Dashboard</h1>
    <p class="sub">Devam etmek icin giris yapin</p>
    <div class="login-field">
      <label for="login-username">Kullanici Adi</label>
      <input type="text" id="login-username" autocomplete="username">
    </div>
    <div class="login-field">
      <label for="login-password">Parola</label>
      <input type="password" id="login-password" autocomplete="current-password">
    </div>
    <button id="login-btn" onclick="doLogin()">Giris Yap</button>
    <div id="login-error"></div>
  </div>
</div>

<div id="app-view">
<header>
  <div>
    <h1>KI Enterprise Dashboard</h1>
    <div class="sub" id="ts">yukleniyor...</div>
  </div>
  <div class="header-actions">
    <button class="btn secondary" onclick="loadActiveTab()">Yenile</button>
    <button class="btn secondary" onclick="doLogout()">Cikis</button>
  </div>
</header>
<nav id="tabs"></nav>
<main id="panels"></main>
</div>

<script>
const CHIEFS = [
  {key:"ceo", label:"CEO"}, {key:"coo", label:"COO"}, {key:"cto", label:"CTO"},
  {key:"cfo", label:"CFO"}, {key:"cpo", label:"CPO"}, {key:"cmo", label:"CMO"},
  {key:"cro", label:"CRO"}, {key:"ciso", label:"CISO"}, {key:"cdo", label:"CDO"},
];
const TABS = [{key:"chat", label:"Chat Odasi"}, ...CHIEFS.map(c => ({key:"chief:"+c.key, label:c.label})), {key:"system", label:"System"}, {key:"dispatch", label:"Gorev Gonder"}, {key:"integrations", label:"Integrations"}];

let TOKEN = sessionStorage.getItem("ki_dashboard_token") || "";
let activeTab = "chat";
const chiefCache = {};
let roomPollTimer = null;
let roomChiefLabels = {};

function authHeaders() { return { "Authorization": "Bearer " + TOKEN }; }

async function getJSON(path) {
  const r = await fetch(path, { headers: authHeaders() });
  if (r.status === 401) { doLogout(); throw new Error("Oturum gecersiz, tekrar giris yapin"); }
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
}

async function doLogin() {
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;
  const errEl = document.getElementById("login-error");
  const btn = document.getElementById("login-btn");
  if (!username || !password) { errEl.textContent = "Kullanici adi ve parola gerekli."; return; }
  btn.disabled = true;
  errEl.textContent = "";
  try {
    const r = await fetch("/api/v1/dashboard/auth/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const body = await r.json();
    if (!r.ok) { errEl.textContent = body.detail || "Giris basarisiz."; btn.disabled = false; return; }
    TOKEN = body.token;
    sessionStorage.setItem("ki_dashboard_token", TOKEN);
    showApp();
  } catch (e) {
    errEl.textContent = "Baglanti hatasi: " + e.message;
  } finally {
    btn.disabled = false;
  }
}

function doLogout() {
  sessionStorage.removeItem("ki_dashboard_token");
  TOKEN = "";
  document.getElementById("app-view").style.display = "none";
  document.getElementById("login-view").style.display = "flex";
  document.getElementById("login-password").value = "";
}

function showApp() {
  document.getElementById("login-view").style.display = "none";
  document.getElementById("app-view").style.display = "block";
  buildTabs();
  loadActiveTab();
}

function buildTabs() {
  const nav = document.getElementById("tabs");
  const panels = document.getElementById("panels");
  nav.innerHTML = "";
  panels.innerHTML = "";
  for (const t of TABS) {
    const btn = document.createElement("button");
    btn.textContent = t.label;
    btn.dataset.tab = t.key;
    btn.className = t.key === activeTab ? "active" : "";
    btn.onclick = () => switchTab(t.key);
    nav.appendChild(btn);

    const panel = document.createElement("div");
    panel.className = "tab-panel" + (t.key === activeTab ? " active" : "");
    panel.id = "panel-" + t.key;
    panel.innerHTML = '<div class="loading">yukleniyor...</div>';
    panels.appendChild(panel);
  }
}

function switchTab(key) {
  activeTab = key;
  if (key !== "chat" && roomPollTimer) { clearInterval(roomPollTimer); roomPollTimer = null; }
  document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("active", b.dataset.tab === key));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.toggle("active", p.id === "panel-" + key));
  loadActiveTab();
}

function loadActiveTab() {
  document.getElementById("ts").textContent = "yukleniyor...";
  const done = () => { document.getElementById("ts").textContent = "son guncelleme: " + new Date().toLocaleTimeString("tr-TR"); };
  if (activeTab === "chat") {
    loadChatRoom().then(done);
  } else if (activeTab.startsWith("chief:")) {
    loadChief(activeTab.slice(6)).then(done);
  } else if (activeTab === "system") {
    loadSystem().then(done);
  } else if (activeTab === "dispatch") {
    loadDispatch().then(done);
  } else if (activeTab === "integrations") {
    loadIntegrations().then(done);
  }
}

function fmtKpiValue(entry) {
  if (entry.value === null || entry.value === undefined) return "-";
  if (entry.unit === "percent") return entry.value + "%";
  if (entry.unit === "currency") return Number(entry.value).toLocaleString("tr-TR");
  return entry.value;
}

function kpiTileHtml(chief, kpi, auto, manual) {
  let badgeCls = "missing", badgeText = "veri yok", valueHtml, noteHtml = "";
  if (auto) {
    badgeCls = "auto"; badgeText = "otomatik";
    valueHtml = `<div class="kpi-value">${fmtKpiValue(auto)}</div>`;
    if (auto.note) noteHtml = `<div class="kpi-note">${auto.note}</div>`;
  } else if (manual) {
    badgeCls = "manual"; badgeText = "manuel";
    valueHtml = `<div class="kpi-value">${fmtKpiValue(manual)}</div>`;
    noteHtml = `<div class="kpi-note">${manual.entered_at ? "girildi: " + manual.entered_at : ""}${manual.note ? " - " + manual.note : ""}</div>`;
  } else {
    valueHtml = `<div class="kpi-value empty">Veri kaynagi henuz yok</div>`;
    noteHtml = `<button class="kpi-fill-btn" onclick="openMetricForm('${chief}','${kpi.key}')">Deger gir</button>`;
  }
  return `<div class="kpi-tile"><span class="kpi-badge ${badgeCls}">${badgeText}</span>
    <div class="kpi-label">${kpi.label}</div>${valueHtml}${noteHtml}</div>`;
}

function openMetricForm(chief, kpiKey) {
  const sel = document.getElementById("metric-kpi-" + chief);
  if (sel) sel.value = kpiKey;
  const anchor = document.getElementById("metric-form-anchor-" + chief);
  if (anchor) anchor.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function submitMetric(chief) {
  const kpiKey = document.getElementById("metric-kpi-" + chief).value;
  const value = document.getElementById("metric-value-" + chief).value.trim();
  const note = document.getElementById("metric-note-" + chief).value.trim();
  const resultEl = document.getElementById("metric-result-" + chief);
  if (!kpiKey || !value) { resultEl.innerHTML = `<span class="err">KPI ve deger gerekli.</span>`; return; }
  resultEl.innerHTML = `<span class="loading">gonderiliyor...</span>`;
  try {
    const numValue = isNaN(Number(value)) ? value : Number(value);
    const r = await fetch(`/api/v1/dashboard/metrics/${chief}/${kpiKey}`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ value: numValue, note }),
    });
    const body = await r.json();
    if (!r.ok) { resultEl.innerHTML = `<span class="err">HTTP ${r.status}: ${body.detail || JSON.stringify(body)}</span>`; return; }
    resultEl.innerHTML = `<span style="color:var(--ok)">Kaydedildi.</span>`;
    delete chiefCache[chief];
    loadChief(chief);
  } catch (e) {
    resultEl.innerHTML = `<span class="err">Hata: ${e.message}</span>`;
  }
}

function deptTableHtml(departments) {
  if (!departments || !departments.length) return `<div class="hint">Bu Chief'e bagli aktif departman yok.</div>`;
  let html = `<table><tr><th>Departman</th><th>Backlog</th><th>Teslimat</th></tr>`;
  for (const d of departments) {
    html += `<tr><td>${d.department}${d.degraded ? " ⚠" : ""}</td><td>${d.backlog_count}</td><td>${d.deliverables_count}</td></tr>`;
  }
  html += "</table>";
  return html;
}

function stageBreakdownHtml(breakdown) {
  if (!breakdown) return "";
  const rows = Object.entries(breakdown);
  if (!rows.length) return "";
  let html = `<div class="card"><h2>Pipeline - Stage Kirilimi (Twenty CRM)</h2><table><tr><th>Stage</th><th>Adet</th><th>Toplam Deger</th></tr>`;
  for (const [stage, v] of rows) {
    html += `<tr><td>${stage}</td><td>${v.count}</td><td>${Number(v.amount).toLocaleString("tr-TR")}</td></tr>`;
  }
  html += "</table></div>";
  return html;
}

async function loadChief(chief) {
  const el = document.getElementById("panel-chief:" + chief);
  const label = (CHIEFS.find(c => c.key === chief) || {}).label || chief.toUpperCase();
  try {
    const d = await getJSON(`/api/v1/dashboard/chief/${chief}`);
    chiefCache[chief] = d;
    const catalog = d.kpi_catalog || [];
    const auto = d.auto_kpis || {};
    const manual = d.manual_kpis || {};

    let html = `<div class="section-title">${label} - KPI'lar</div><div class="kpi-grid">`;
    for (const kpi of catalog) {
      html += kpiTileHtml(chief, kpi, auto[kpi.key], manual[kpi.key]);
    }
    html += "</div>";

    html += stageBreakdownHtml(auto._stage_breakdown);

    html += `<div class="card"><h2>${label} - Departmanlar</h2>${deptTableHtml(d.departments)}</div>`;

    html += `<div class="card" id="metric-form-anchor-${chief}"><h2>Manuel KPI Girisi</h2>
      <div class="metric-form">
        <select id="metric-kpi-${chief}">${catalog.map(k => `<option value="${k.key}">${k.label}</option>`).join("")}</select>
        <input type="text" id="metric-value-${chief}" placeholder="deger (sayi veya metin)">
        <input type="text" id="metric-note-${chief}" placeholder="not (opsiyonel)">
        <button onclick="submitMetric('${chief}')">Kaydet</button>
      </div>
      <div class="metric-result" id="metric-result-${chief}"></div>
    </div>`;

    if (d.degraded) html += `<div class="err">Bazi veriler eksik olabilir: ${(d.errors || []).join("; ")}</div>`;
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = `<div class="err">Yuklenemedi: ${e.message}</div>`;
  }
}

function badge(status) {
  const cls = status === "ok" ? "ok" : (status === "degraded" ? "degraded" : "unreachable");
  return `<span class="badge ${cls}">${status}</span>`;
}

async function loadSystem() {
  const el = document.getElementById("panel-system");
  try {
    const d = await getJSON("/api/v1/dashboard/system");
    let html = `<div class="card"><h2>System</h2><div class="stat-row"><div class="stat"><div class="n">${d.healthy_count}/${d.total_count}</div><div class="l">servis saglikli</div></div></div><table>`;
    for (const s of d.services) html += `<tr><td>${s.service}</td><td>${badge(s.status)}</td></tr>`;
    html += "</table></div>";
    el.innerHTML = html;
  } catch (e) { el.innerHTML = `<div class="err">Yuklenemedi: ${e.message}</div>`; }
}

function integStatusBadge(status) {
  const s = (status || "").toUpperCase();
  const cls = s === "ACTIVE" ? "ok" : (s === "PENDING" ? "degraded" : (s ? "unreachable" : "degraded"));
  return `<span class="badge ${cls}">${escapeHtml(status || "?")}</span>`;
}

function integItemHtml(item) {
  const isCustom = item.source === "custom";
  const actions = isCustom
    ? `<div class="integ-actions">
         <button onclick="editCustomIntegration('${escapeHtml(item.id)}')">Duzenle</button>
         <button onclick="deleteCustomIntegration('${escapeHtml(item.id)}')">Sil</button>
       </div>`
    : `<div class="integ-identity">${escapeHtml(item.source)}</div>`;
  return `<div class="integ-item">
    <div>
      <div class="integ-name">${escapeHtml(item.name)} ${integStatusBadge(item.status)}</div>
      <div class="integ-identity">${escapeHtml(item.identity || "")}</div>
      ${item.notes ? `<div class="integ-identity">${escapeHtml(item.notes)}</div>` : ""}
    </div>
    ${actions}
  </div>`;
}

let customIntegrationsCache = [];

async function loadIntegrations() {
  const el = document.getElementById("panel-integrations");
  try {
    const [d, customResp] = await Promise.all([
      getJSON("/api/v1/dashboard/integrations"),
      getJSON("/api/v1/dashboard/integrations/custom"),
    ]);
    customIntegrationsCache = customResp.items || [];

    let html = `<div class="integ-grid">`;
    for (const cat of d.categories || []) {
      html += `<div class="card integ-card"><h2>${escapeHtml(cat.label)} <span class="integ-count">${cat.items.length}</span></h2>`;
      html += cat.items.length ? cat.items.map(integItemHtml).join("") : `<div class="hint">Henuz baglanti yok.</div>`;
      html += `</div>`;
    }
    html += `</div>`;

    if (d.composio_error) html += `<div class="err">Composio servisine erisilemedi: ${escapeHtml(d.composio_error)}</div>`;

    const catOptions = (d.categories || []).map(c => `<option value="${c.key}">${escapeHtml(c.label)}</option>`).join("");
    html += `<div class="card" id="integ-form-anchor">
      <h2>Yeni Entegrasyon Ekle / Duzenle</h2>
      <div class="integ-form">
        <input type="hidden" id="integ-id">
        <input type="text" id="integ-name" placeholder="Ad (orn. QuickBooks)">
        <select id="integ-category">${catOptions}</select>
        <input type="text" id="integ-base-url" placeholder="URL (opsiyonel)">
        <input type="password" id="integ-api-key" placeholder="API Key (opsiyonel)">
        <input type="text" id="integ-notes" placeholder="Not (opsiyonel)">
        <button onclick="submitCustomIntegration()">Kaydet</button>
        <button onclick="resetIntegrationForm()" style="background:transparent;border:1px solid var(--border);color:var(--muted)">Temizle</button>
      </div>
      <div class="hint">Composio uzerinden gercek bir app baglamak icin Chat Odasi'ndan CEO/Chief'e "composio ile X'e baglan" seklinde talep iletebilirsin. URL/API key girip kaydetmen, o entegrasyonu hemen "bagli" olarak isaretler - ayri bir OAuth adimi yoktur.</div>
      <div class="dispatch-result" id="integ-form-result"></div>
    </div>`;

    el.innerHTML = html;
  } catch (e) { el.innerHTML = `<div class="err">Yuklenemedi: ${e.message}</div>`; }
}

function resetIntegrationForm() {
  document.getElementById("integ-id").value = "";
  document.getElementById("integ-name").value = "";
  document.getElementById("integ-base-url").value = "";
  document.getElementById("integ-api-key").value = "";
  document.getElementById("integ-notes").value = "";
  document.getElementById("integ-form-result").innerHTML = "";
}

function editCustomIntegration(id) {
  const item = customIntegrationsCache.find(c => c.id === id);
  if (!item) return;
  document.getElementById("integ-id").value = item.id;
  document.getElementById("integ-name").value = item.name || "";
  document.getElementById("integ-category").value = item.category || "other";
  document.getElementById("integ-base-url").value = item.base_url || "";
  document.getElementById("integ-api-key").value = "";
  document.getElementById("integ-api-key").placeholder = item.api_key ? `Mevcut: ${item.api_key} (degistirmek icin yaz)` : "API Key (opsiyonel)";
  document.getElementById("integ-notes").value = item.notes || "";
  document.getElementById("integ-form-anchor").scrollIntoView({ behavior: "smooth", block: "center" });
}

async function deleteCustomIntegration(id) {
  if (!confirm("Bu entegrasyon kaydini silmek istedigine emin misin?")) return;
  try {
    const r = await fetch(`/api/v1/dashboard/integrations/custom/${id}`, { method: "DELETE", headers: authHeaders() });
    if (!r.ok) throw new Error("HTTP " + r.status);
    loadIntegrations();
  } catch (e) { alert("Silinemedi: " + e.message); }
}

async function submitCustomIntegration() {
  const resultEl = document.getElementById("integ-form-result");
  const name = document.getElementById("integ-name").value.trim();
  if (!name) { resultEl.innerHTML = `<span class="err">Ad gerekli.</span>`; return; }
  const payload = {
    id: document.getElementById("integ-id").value.trim(),
    name,
    category: document.getElementById("integ-category").value,
    base_url: document.getElementById("integ-base-url").value.trim(),
    api_key: document.getElementById("integ-api-key").value.trim(),
    notes: document.getElementById("integ-notes").value.trim(),
  };
  resultEl.innerHTML = `<span class="loading">kaydediliyor...</span>`;
  try {
    const r = await fetch("/api/v1/dashboard/integrations/custom", {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await r.json();
    if (!r.ok) { resultEl.innerHTML = `<span class="err">HTTP ${r.status}: ${body.detail || JSON.stringify(body)}</span>`; return; }
    resultEl.innerHTML = `<span style="color:var(--ok)">Kaydedildi.</span>`;
    resetIntegrationForm();
    loadIntegrations();
  } catch (e) { resultEl.innerHTML = `<span class="err">Hata: ${e.message}</span>`; }
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

function getActiveRoomChiefs() {
  return Array.from(document.querySelectorAll(".room-chief-toggle input[data-chief]:checked")).map(i => i.dataset.chief);
}

function onRoomChiefToggle() {
  localStorage.setItem("ki_room_active_chiefs", JSON.stringify(getActiveRoomChiefs()));
}

function onRoomInputKeydown(e) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendRoomMessage(); }
}

function roomMsgHtml(m) {
  const roleCls = "role-" + (m.role || "ceo");
  const isReport = m.type === "daily_report";
  const dispatchHtml = (m.dispatch && m.dispatch.workflow_id)
    ? `<div class="room-msg-dispatch">✓ Is baslatildi: ${escapeHtml(m.dispatch.workflow_id)}</div>` : "";
  const speaker = m.speaker || (m.role === "user" ? "Sen" : m.role);
  return `<div class="room-msg ${roleCls}${isReport ? " report" : ""}">
    <div class="room-msg-speaker">${escapeHtml(speaker)}${isReport ? " · Otomatik Rapor" : ""}</div>
    ${escapeHtml(m.text)}${dispatchHtml}
  </div>`;
}

async function refreshRoomHistory() {
  try {
    const d = await getJSON("/api/v1/dashboard/room/history?limit=50");
    const el = document.getElementById("room-messages");
    if (!el) return;
    const wasAtBottom = (el.scrollTop + el.clientHeight) >= (el.scrollHeight - 30);
    el.innerHTML = (d.messages || []).map(roomMsgHtml).join("") || `<div class="hint">Henuz mesaj yok - asagidan yazmaya baslayabilirsin.</div>`;
    if (wasAtBottom) el.scrollTop = el.scrollHeight;
  } catch (e) { /* polling hatasi sessiz gecilir, kullaniciyi her 15sn'de rahatsiz etmesin */ }
}

async function sendRoomMessage() {
  const input = document.getElementById("room-input");
  const btn = document.getElementById("room-send-btn");
  const message = input.value.trim();
  if (!message) return;
  const activeChiefs = getActiveRoomChiefs();
  input.value = "";
  btn.disabled = true;
  const el = document.getElementById("room-messages");
  el.insertAdjacentHTML("beforeend", roomMsgHtml({ role: "user", speaker: "Sen", text: message }));
  el.scrollTop = el.scrollHeight;
  try {
    const r = await fetch("/api/v1/dashboard/room/message", {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ message, active_chiefs: activeChiefs }),
    });
    if (r.status === 401) { doLogout(); return; }
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      el.insertAdjacentHTML("beforeend", `<div class="err">Hata: ${escapeHtml(body.detail || ("HTTP " + r.status))}</div>`);
    }
  } catch (e) {
    el.insertAdjacentHTML("beforeend", `<div class="err">Baglanti hatasi: ${escapeHtml(e.message)}</div>`);
  } finally {
    btn.disabled = false;
    await refreshRoomHistory();
  }
}

async function loadChatRoom() {
  const el = document.getElementById("panel-chat");
  try {
    const d = await getJSON("/api/v1/dashboard/room/chiefs");
    roomChiefLabels = d.labels || {};
    let saved = [];
    try { saved = JSON.parse(localStorage.getItem("ki_room_active_chiefs") || "[]"); } catch (e) { saved = []; }
    const toggles = (d.chiefs || []).map(c => `
      <label class="room-chief-toggle">
        <input type="checkbox" data-chief="${c}" ${saved.includes(c) ? "checked" : ""} onchange="onRoomChiefToggle()">
        ${escapeHtml(roomChiefLabels[c] || c.toUpperCase())}
      </label>`).join("");
    el.innerHTML = `<div class="room-wrap">
      <div class="room-participants">
        <h2>Odadakiler</h2>
        <div class="room-chief-toggle ceo-fixed"><input type="checkbox" checked disabled> CEO (John)</div>
        ${toggles}
        <div class="hint" style="margin-top:10px">Diger Chief'leri ekleyip cikarabilirsin - John her zaman odadadir ve koordine eder.</div>
      </div>
      <div class="room-main">
        <div class="room-messages" id="room-messages"><div class="loading">yukleniyor...</div></div>
        <div class="room-input-row">
          <textarea id="room-input" placeholder="Mesaj yaz... (Enter ile gonder, Shift+Enter yeni satir)" onkeydown="onRoomInputKeydown(event)"></textarea>
          <button id="room-send-btn" onclick="sendRoomMessage()">Gonder</button>
        </div>
      </div>
    </div>`;
    await refreshRoomHistory();
    if (roomPollTimer) clearInterval(roomPollTimer);
    roomPollTimer = setInterval(refreshRoomHistory, 15000);
  } catch (e) {
    el.innerHTML = `<div class="err">Yuklenemedi: ${e.message}</div>`;
  }
}

async function loadDispatch() {
  const el = document.getElementById("panel-dispatch");
  el.innerHTML = `<div class="card dispatch-card">
    <h2>Gorev Gonder (Chief / Departman)</h2>
    <div class="dispatch-form">
      <select id="dispatch-workflow"><option>yukleniyor...</option></select>
      <input type="text" id="dispatch-project" placeholder="proje (opsiyonel)">
      <textarea id="dispatch-prompt" placeholder="Gorev/talep aciklamasi..."></textarea>
      <button onclick="submitDispatch()">Gonder</button>
    </div>
    <div class="dispatch-result" id="dispatch-result"></div>
  </div>`;
  try {
    const d = await getJSON("/api/v1/dashboard/workflows");
    document.getElementById("dispatch-workflow").innerHTML = d.workflows.map(w => `<option value="${w}">${w}</option>`).join("");
  } catch (e) {
    document.getElementById("dispatch-workflow").innerHTML = `<option>yuklenemedi</option>`;
  }
}

async function submitDispatch() {
  const resultEl = document.getElementById("dispatch-result");
  const workflow = document.getElementById("dispatch-workflow").value;
  const project = document.getElementById("dispatch-project").value;
  const prompt = document.getElementById("dispatch-prompt").value.trim();
  if (!prompt) { resultEl.innerHTML = `<span class="err">Gorev aciklamasi bos olamaz.</span>`; return; }
  resultEl.innerHTML = `<span class="loading">gonderiliyor...</span>`;
  try {
    const r = await fetch("/api/v1/dashboard/dispatch", {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ workflow, project, prompt }),
    });
    const body = await r.json();
    if (!r.ok) { resultEl.innerHTML = `<span class="err">HTTP ${r.status}: ${JSON.stringify(body)}</span>`; return; }
    resultEl.innerHTML = `<span style="color:var(--ok)">Gonderildi: workflow_id=${body.workflow_id || "?"}, status=${body.status || "?"}</span>`;
  } catch (e) { resultEl.innerHTML = `<span class="err">Hata: ${e.message}</span>`; }
}

if (TOKEN) { showApp(); } else { document.getElementById("login-view").style.display = "flex"; }
</script>
</body>
</html>"""
