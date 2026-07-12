"""KI Enterprise Dashboard - basit web arayuzu (Phase 9 eklentisi).

Tek sayfa, sunucu-tarafinda render edilmeyen, tarayicida ayni-origin API
uclarina (bkz. main.py) fetch() ile baglanan statik bir HTML/JS sayfasi.
INTERNAL_API_KEY sayfaya GOMULUDUR (bu ic-ag/guvenilir-agdaki tum servislerin
zaten paylastigi ayni sirdir, projede kurulu tehdit modeliyle tutarlidir -
gercekten internete acilirsa Traefik BasicAuth + bu key iki katmanli koruma
saglar, ama tek basina kripto-guvenli bir kimlik dogrulama DEGILDIR)."""

def render_dashboard_html(internal_api_key: str) -> str:
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KI Enterprise Dashboard</title>
<style>
  :root {{
    --bg: #0b0e14; --panel: #131722; --border: #232838; --text: #e6e9ef;
    --muted: #8b93a7; --ok: #3ecf8e; --bad: #ef5350; --warn: #f0b429; --accent: #5b8def;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,Segoe UI,Roboto,sans-serif; }}
  header {{ padding:20px 28px; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; }}
  header h1 {{ font-size:18px; margin:0; font-weight:600; }}
  header .sub {{ color:var(--muted); font-size:13px; margin-top:2px; }}
  #refresh {{ background:var(--accent); color:#fff; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; font-size:13px; }}
  #refresh:hover {{ opacity:0.85; }}
  main {{ padding:24px 28px; display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:18px; }}
  .card {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:18px; }}
  .card h2 {{ font-size:14px; margin:0 0 14px; color:var(--muted); text-transform:uppercase; letter-spacing:0.05em; }}
  .stat-row {{ display:flex; gap:16px; flex-wrap:wrap; margin-bottom:12px; }}
  .stat {{ flex:1; min-width:80px; }}
  .stat .n {{ font-size:26px; font-weight:700; }}
  .stat .l {{ font-size:11px; color:var(--muted); margin-top:2px; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; }}
  .badge.ok {{ background:rgba(62,207,142,0.15); color:var(--ok); }}
  .badge.degraded {{ background:rgba(240,180,41,0.15); color:var(--warn); }}
  .badge.unreachable {{ background:rgba(239,83,80,0.15); color:var(--bad); }}
  ul.svc {{ list-style:none; margin:0; padding:0; }}
  ul.svc li {{ display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid var(--border); font-size:13px; }}
  ul.svc li:last-child {{ border-bottom:none; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  table th {{ text-align:left; color:var(--muted); font-weight:500; padding:6px 4px; border-bottom:1px solid var(--border); }}
  table td {{ padding:6px 4px; border-bottom:1px solid var(--border); }}
  .loading {{ color:var(--muted); font-size:13px; }}
  .err {{ color:var(--bad); font-size:12px; margin-top:8px; }}
  .disclaimer {{ color:var(--muted); font-size:11px; font-style:italic; margin-top:10px; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>KI Enterprise Dashboard</h1>
    <div class="sub" id="ts">yukleniyor...</div>
  </div>
  <button id="refresh" onclick="loadAll()">Yenile</button>
</header>
<main id="grid">
  <div class="card" id="card-system"><h2>System</h2><div class="loading">yukleniyor...</div></div>
  <div class="card" id="card-ceo"><h2>CEO</h2><div class="loading">yukleniyor...</div></div>
  <div class="card" id="card-departments"><h2>Departments</h2><div class="loading">yukleniyor...</div></div>
  <div class="card" id="card-projects"><h2>Projects</h2><div class="loading">yukleniyor...</div></div>
  <div class="card" id="card-finance"><h2>Finance</h2><div class="loading">yukleniyor...</div></div>
  <div class="card" id="card-marketing"><h2>Marketing</h2><div class="loading">yukleniyor...</div></div>
</main>
<script>
const KEY = "{internal_api_key}";
const H = {{ "Authorization": "Bearer " + KEY }};

async function getJSON(path) {{
  const r = await fetch(path, {{ headers: H }});
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
}}

function badge(status) {{
  const cls = status === "ok" ? "ok" : (status === "degraded" ? "degraded" : "unreachable");
  return `<span class="badge ${{cls}}">${{status}}</span>`;
}}

async function loadSystem() {{
  const el = document.getElementById("card-system");
  try {{
    const d = await getJSON("/api/v1/dashboard/system");
    let html = `<h2>System</h2><div class="stat-row"><div class="stat"><div class="n">${{d.healthy_count}}/${{d.total_count}}</div><div class="l">servis saglikli</div></div></div><ul class="svc">`;
    for (const s of d.services) {{
      html += `<li><span>${{s.service}}</span>${{badge(s.status)}}</li>`;
    }}
    html += "</ul>";
    el.innerHTML = html;
  }} catch (e) {{ el.innerHTML = `<h2>System</h2><div class="err">Yuklenemedi: ${{e.message}}</div>`; }}
}}

async function loadCeo() {{
  const el = document.getElementById("card-ceo");
  try {{
    const d = await getJSON("/api/v1/dashboard/ceo");
    let html = `<h2>CEO</h2><div class="stat-row"><div class="stat"><div class="n">${{d.total_decisions}}</div><div class="l">toplam karar</div></div></div>`;
    html += "<table><tr><th>Durum</th><th>Adet</th></tr>";
    for (const [k, v] of Object.entries(d.by_status)) html += `<tr><td>${{k}}</td><td>${{v}}</td></tr>`;
    html += "</table>";
    if (d.degraded) html += `<div class="err">Bazi veriler eksik olabilir</div>`;
    el.innerHTML = html;
  }} catch (e) {{ el.innerHTML = `<h2>CEO</h2><div class="err">Yuklenemedi: ${{e.message}}</div>`; }}
}}

async function loadDepartments() {{
  const el = document.getElementById("card-departments");
  try {{
    const d = await getJSON("/api/v1/dashboard/departments");
    let html = `<h2>Departments</h2><table><tr><th>Departman</th><th>Backlog</th><th>Teslimat</th></tr>`;
    for (const dep of d.departments) {{
      html += `<tr><td>${{dep.department}}${{dep.degraded ? " ⚠" : ""}}</td><td>${{dep.backlog_count}}</td><td>${{dep.deliverables_count}}</td></tr>`;
    }}
    html += "</table>";
    el.innerHTML = html;
  }} catch (e) {{ el.innerHTML = `<h2>Departments</h2><div class="err">Yuklenemedi: ${{e.message}}</div>`; }}
}}

async function loadProjects() {{
  const el = document.getElementById("card-projects");
  try {{
    const d = await getJSON("/api/v1/dashboard/projects");
    let html = `<h2>Projects</h2><table><tr><th>Proje</th><th>Backlog</th><th>Teslimat</th><th>Maliyet</th></tr>`;
    for (const p of d.projects) {{
      if (p.status === "unavailable") {{
        html += `<tr><td>${{p.project}}</td><td colspan="3" class="err">erisilemedi</td></tr>`;
      }} else {{
        html += `<tr><td>${{p.project}}${{p.degraded ? " ⚠" : ""}}</td><td>${{p.backlog_count}}</td><td>${{p.deliverables_count}}</td><td>${{p.cost_flagged_count}}</td></tr>`;
      }}
    }}
    html += "</table>";
    el.innerHTML = html;
  }} catch (e) {{ el.innerHTML = `<h2>Projects</h2><div class="err">Yuklenemedi: ${{e.message}}</div>`; }}
}}

async function loadFinance() {{
  const el = document.getElementById("card-finance");
  try {{
    const d = await getJSON("/api/v1/dashboard/finance");
    let html = `<h2>Finance</h2><div class="stat-row">`;
    html += `<div class="stat"><div class="n">${{d.total_cost_flagged_items}}</div><div class="l">maliyet-isaretli is</div></div>`;
    html += `<div class="stat"><div class="n">${{d.expired_approval_count}}</div><div class="l">suresi dolmus onay</div></div>`;
    html += "</div>";
    if (d.items && d.items.length) {{
      html += "<table><tr><th>Proje</th><th>Workflow</th><th>Durum</th></tr>";
      for (const i of d.items.slice(0, 5)) html += `<tr><td>${{i.project}}</td><td>${{i.workflow}}</td><td>${{i.approval_status}}</td></tr>`;
      html += "</table>";
    }}
    html += `<div class="disclaimer">${{d.disclaimer}}</div>`;
    el.innerHTML = html;
  }} catch (e) {{ el.innerHTML = `<h2>Finance</h2><div class="err">Yuklenemedi: ${{e.message}}</div>`; }}
}}

async function loadMarketing() {{
  const el = document.getElementById("card-marketing");
  try {{
    const d = await getJSON("/api/v1/dashboard/marketing");
    let html = `<h2>Marketing</h2><div class="stat-row">`;
    html += `<div class="stat"><div class="n">${{d.backlog.length}}</div><div class="l">backlog</div></div>`;
    html += `<div class="stat"><div class="n">${{d.deliverables.length}}</div><div class="l">teslimat</div></div>`;
    html += "</div>";
    el.innerHTML = html;
  }} catch (e) {{ el.innerHTML = `<h2>Marketing</h2><div class="err">Yuklenemedi: ${{e.message}}</div>`; }}
}}

async function loadAll() {{
  document.getElementById("ts").textContent = "yukleniyor...";
  await Promise.all([loadSystem(), loadCeo(), loadDepartments(), loadProjects(), loadFinance(), loadMarketing()]);
  document.getElementById("ts").textContent = "son guncelleme: " + new Date().toLocaleTimeString("tr-TR");
}}

loadAll();
</script>
</body>
</html>"""
