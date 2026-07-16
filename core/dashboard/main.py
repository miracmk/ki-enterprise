"""
KI Enterprise Dashboard (Phase 9).

Build order'daki panel setine karsilik gelir: CEO/Department/Project/Finance/
Marketing/System Dashboard. Bu servis bir ARKA UC (backend API) - frontend/UI
katmani yok, her panel icin JSON konsolide gorunum doner.

Onceki fazlardan (6/8) ogrenilen dersler BASTAN uygulanir:
  - Tum coklu-kaynak sorgular PARALEL (asyncio.gather) - sirali N+1 anti-pattern'i
    Project Manager (Phase 6) ve Aethris'te (Phase 8) bulunup duzeltilmisti.
  - Tek bir alt-servisin hatasi/beklenmedik semasi TUM paneli dusurmez -
    her yardimci fonksiyon hata durumunda None/bos doner, dogrudan dict
    indekslemesi (Aethris Phase 8 K2) kullanilmaz.
"""
import asyncio
import logging
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from config import settings
from static_ui import render_dashboard_html

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard")

# Tek dogruluk kaynagi core.env:WORKFLOW_TO_DEPARTMENT'tir - dinamik turetilir.
DISPATCHABLE_WORKFLOWS = list(settings.WORKFLOW_TO_DEPARTMENT.keys())

ALL_SERVICES = {
    "ceo": settings.CEO_API_URL,
    "memory": settings.MEMORY_API_URL,
    "ai_gateway": settings.AI_GATEWAY_URL,
    "executives": settings.EXECUTIVES_API_URL,
    "departments": settings.DEPARTMENTS_API_URL,
    "workers": settings.WORKERS_API_URL,
    "projects": settings.PROJECTS_API_URL,
    "skills": settings.SKILLS_API_URL,
    "finance": settings.FINANCE_API_URL,
    "composio": settings.COMPOSIO_API_URL,
}

CHIEFS = ["ceo", "coo", "cto", "cfo", "cpo", "cmo", "cro", "ciso", "cdo"]
CHIEF_LABELS = {
    "ceo": "CEO", "coo": "COO", "cto": "CTO", "cfo": "CFO", "cpo": "CPO",
    "cmo": "CMO", "cro": "CRO", "ciso": "CISO", "cdo": "CDO",
}

# Kullanicinin verdigi Chief-bazli KPI listesi - dashboard/chief/{chief} bu
# katalogla auto_kpis/manual_kpis arasindaki bosluklari doldurur (bir KPI
# icin ne auto ne manuel deger varsa UI "veri kaynagi henuz yok" gosterir).
# (key, gorunur_ad) - key ayni zamanda manuel giris ucunun path parametresi.
CHIEF_KPI_CATALOG: dict[str, list[tuple[str, str]]] = {
    "ceo": [
        ("arr_mrr_growth", "ARR / MRR Growth"), ("revenue_growth", "Revenue Growth %"),
        ("ebitda", "EBITDA"), ("net_profit_margin", "Net Profit Margin"),
        ("company_valuation", "Company Valuation"), ("clv", "Customer Lifetime Value (CLV)"),
        ("enps", "Employee Satisfaction (eNPS)"), ("okr_completion", "Company OKR Completion"),
        ("strategic_initiative_success", "Strategic Initiative Success Rate"),
        ("board_kpi_achievement", "Board KPI Achievement"), ("cash_runway", "Cash Runway"),
        ("market_share", "Market Share"),
    ],
    "coo": [
        ("sla_compliance", "SLA Compliance"), ("operational_efficiency", "Operational Efficiency"),
        ("avg_resolution_time", "Average Resolution Time"), ("csat", "Customer Satisfaction (CSAT)"),
        ("employee_productivity", "Employee Productivity"), ("procurement_savings", "Procurement Savings"),
        ("cost_per_ticket", "Cost per Ticket"), ("support_backlog", "Support Backlog"),
        ("process_automation", "Process Automation %"), ("internal_cycle_time", "Internal Process Cycle Time"),
    ],
    "cto": [
        ("deployment_frequency", "Deployment Frequency"), ("lead_time_for_changes", "Lead Time for Changes"),
        ("mttr", "Mean Time To Recovery (MTTR)"), ("change_failure_rate", "Change Failure Rate"),
        ("engineering_velocity", "Engineering Velocity"), ("sprint_predictability", "Sprint Predictability"),
        ("system_availability", "System Availability"), ("api_uptime", "API Uptime"),
        ("bug_escape_rate", "Bug Escape Rate"), ("technical_debt_ratio", "Technical Debt Ratio"),
        ("infrastructure_cost", "Infrastructure Cost"), ("ai_model_performance", "AI Model Performance"),
    ],
    "cfo": [
        ("revenue", "Revenue"), ("gross_margin", "Gross Margin"), ("net_profit", "Net Profit"),
        ("cash_flow", "Cash Flow"), ("burn_rate", "Burn Rate"), ("cash_runway", "Cash Runway"),
        ("ebitda", "EBITDA"), ("budget_accuracy", "Budget Accuracy"),
        ("tax_compliance", "Tax Compliance"), ("dso", "DSO"), ("collection_rate", "Collection Rate"),
    ],
    "cpo": [
        ("feature_adoption", "Feature Adoption"), ("product_usage", "Product Usage"),
        ("user_retention", "User Retention"), ("dau_mau", "DAU / MAU"), ("churn_rate", "Churn Rate"),
        ("product_nps", "Product NPS"), ("time_to_market", "Time to Market"),
        ("delivery_predictability", "Product Delivery Predictability"),
        ("ux_satisfaction", "UX Satisfaction"), ("product_success_score", "Product Success Score"),
    ],
    "cmo": [
        ("cac", "CAC"), ("mql", "Marketing Qualified Leads"), ("sql_conversion", "SQL Conversion"),
        ("organic_traffic", "Organic Traffic"), ("brand_awareness", "Brand Awareness"),
        ("social_engagement", "Social Engagement"), ("conversion_rate", "Conversion Rate"),
        ("campaign_roi", "Campaign ROI"), ("content_production", "Content Production"),
        ("share_of_voice", "Share of Voice"),
    ],
    "cro": [
        ("arr", "ARR"), ("mrr", "MRR"), ("sales_growth", "Sales Growth"), ("win_rate", "Win Rate"),
        ("pipeline_coverage", "Pipeline Coverage"), ("revenue_retention", "Revenue Retention"),
        ("expansion_revenue", "Expansion Revenue"), ("upsell_rate", "Upsell Rate"),
        ("partnership_revenue", "Partnership Revenue"), ("forecast_accuracy", "Forecast Accuracy"),
    ],
    "ciso": [
        ("security_incidents", "Security Incidents"), ("mttd", "Mean Time To Detect"),
        ("mttr_security", "Mean Time To Respond"), ("vuln_sla", "Vulnerability SLA"),
        ("patch_compliance", "Patch Compliance"), ("security_audit_score", "Security Audit Score"),
        ("compliance_score", "Compliance Score"), ("zero_trust_coverage", "Zero Trust Coverage"),
        ("privacy_compliance", "Privacy Compliance"), ("pentest_findings", "Penetration Test Findings"),
    ],
    "cdo": [
        ("data_quality_score", "Data Quality Score"), ("dashboard_adoption", "Dashboard Adoption"),
        ("ai_dataset_quality", "AI Dataset Quality"), ("data_pipeline_success", "Data Pipeline Success Rate"),
        ("etl_success_rate", "ETL Success Rate"), ("query_performance", "Query Performance"),
        ("data_freshness", "Data Freshness"), ("ml_model_accuracy", "ML Model Accuracy"),
        ("data_governance_compliance", "Data Governance Compliance"),
        ("self_service_bi_usage", "Self-Service BI Usage"),
    ],
}


async def verify_api_key(authorization: str = Header(default="")):
    """Ya ana INTERNAL_API_KEY (sunucu-sunucu cagrilari) YA DA kapsami
    daraltilmis DASHBOARD_UI_TOKEN (SADECE /ui sayfasindan gelen tarayici
    istekleri) kabul edilir. UI token sizarsa (herkese acik sayfa) saldirgan
    sadece Dashboard'un salt-okunur verisini okuyabilir - CEO dispatch/Memory
    yazma gibi TUM sistemi acan ana anahtara ERISEMEZ."""
    valid = (
        secrets.compare_digest(authorization, f"Bearer {settings.INTERNAL_API_KEY}") or
        secrets.compare_digest(authorization, f"Bearer {settings.DASHBOARD_UI_TOKEN}")
    )
    if not valid:
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik Authorization header'i")


async def verify_master_key(authorization: str = Header(default="")):
    """DISPATCH gibi YAZMA/aksiyon-tetikleyen uclar icin - SADECE tam
    INTERNAL_API_KEY kabul edilir, DASHBOARD_UI_TOKEN GECERSIZDIR (verify_api_key'in
    aksine). 2026-07-16: dashboard'a gercek gorev tetikleme eklenirken bilerek
    boyle tasarlandi - /ui sayfasina gomulu token'in "sadece salt-okunur"
    garantisi (bkz. verify_api_key docstring'i) BOZULMASIN diye kullanici bu
    ucu cagirirken master key'i HER SEFERINDE elle girer, sayfaya gomulmez."""
    if not secrets.compare_digest(authorization, f"Bearer {settings.INTERNAL_API_KEY}"):
        raise HTTPException(status_code=401, detail="Bu islem icin tam INTERNAL_API_KEY gerekir (DASHBOARD_UI_TOKEN yeterli degil)")


class DispatchRequest(BaseModel):
    workflow: str
    prompt: str
    project: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class MetricEntryRequest(BaseModel):
    value: float | str
    note: str = ""


async def _safe_get(http: httpx.AsyncClient, url: str, timeout: float = 15.0) -> tuple[dict | None, str | None]:
    """Basarisiz olursa (herhangi bir sebeple) (None, hata_metni) doner - TEK
    bir alt-servis cagrisi tum dashboard panelini dusurmesin diye genis except
    kullanilir. ONEMLI (Fable 5 Phase 9 denetiminde bulunan regresyon):
    eskiden basitce None donuyordu, "servis gercekten 0 veri dondu" ile
    "servise erisilemedi/coktu" AYIRT EDILEMIYORDU - Project Manager'in Phase 6'da
    ozenle korudugu degraded/errors ayrimi burada kaybolmustu, artik geri
    getirildi."""
    try:
        resp = await http.get(url, headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"}, timeout=timeout)
        if resp.status_code != 200:
            err = f"{url}: HTTP {resp.status_code}"
            logger.warning(err)
            return None, err
        return resp.json(), None
    except Exception as e:
        err = f"{url}: {e}"
        logger.warning(err)
        return None, err


async def _dept_view(http: httpx.AsyncClient, dept: str) -> dict:
    (backlog, backlog_err), (deliverables, deliverables_err) = await asyncio.gather(
        _safe_get(http, f"{settings.DEPARTMENTS_API_URL}/api/v1/departments/{dept}/backlog?limit=50"),
        _safe_get(http, f"{settings.WORKERS_API_URL}/api/v1/workers/{dept}/deliverables?limit=50"),
    )
    errors = [e for e in (backlog_err, deliverables_err) if e]
    return {
        "department": dept,
        "backlog_count": len((backlog or {}).get("items", [])),
        "deliverables_count": len((deliverables or {}).get("items", [])),
        "degraded": bool(errors),
        "errors": errors,
    }


async def _twenty_query(http: httpx.AsyncClient, query: str) -> tuple[dict | None, str | None]:
    """twenty-mcp/server.py'deki graphql_query ile ayni desen - dogrudan Twenty
    CRM GraphQL API'sine sorgu, CRO panelinin gercek/canli pipeline verisi icin."""
    if not settings.TWENTY_API_KEY:
        return None, "TWENTY_API_KEY yapilandirilmamis"
    try:
        resp = await http.post(
            settings.TWENTY_API_URL, json={"query": query},
            headers={"Authorization": f"Bearer {settings.TWENTY_API_KEY}", "Content-Type": "application/json"},
            timeout=15.0,
        )
        if resp.status_code != 200:
            return None, f"Twenty CRM: HTTP {resp.status_code}"
        body = resp.json()
        if body.get("errors"):
            return None, f"Twenty CRM: {body['errors'][0]}"
        return body.get("data", {}), None
    except Exception as e:
        return None, f"Twenty CRM: {e}"


async def _get_manual_kpis(http: httpx.AsyncClient, chief: str) -> tuple[dict, str | None]:
    """Manuel girilmis KPI'lardan (bkz. record_metric) her kpi_key icin EN GUNCEL
    degeri doner. Memory retrieve sonucu zaten created_at DESC sirali oldugu icin
    ilk gorulen kayit o kpi_key'in en guncel degeridir."""
    resp, err = await _safe_get(http, f"{settings.MEMORY_API_URL}/api/v1/memory/retrieve?mem_type=global&scope_key=kpi:{chief}&limit=100")
    if resp is None:
        return {}, err
    latest: dict[str, dict] = {}
    for item in resp.get("items", []):
        content = item.get("content")
        if not isinstance(content, dict) or "kpi_key" not in content:
            continue
        k = content["kpi_key"]
        if k not in latest:
            latest[k] = {"value": content.get("value"), "note": content.get("note", ""), "entered_at": content.get("entered_at")}
    return latest, None


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=30.0)
    yield
    await app.state.http.aclose()


app = FastAPI(title="KI Enterprise Dashboard", lifespan=lifespan)


@app.get("/", include_in_schema=False)
async def root():
    """Kok path'te dogrudan bir view yok - kullanicilar /ui'a yonlendirilir
    (2026-07-16: enterprise.kibusiness.co'ya girince 404 gorulmesi bulgusu)."""
    return RedirectResponse(url="/ui")


@app.get("/ui", response_class=HTMLResponse)
async def ui():
    """Basit web arayuzu - HTML/JS sayfasinin kendisi auth GEREKTIRMEZ (bir
    tarayicinin sayfayi indirebilmesi icin). 2026-07-16'dan itibaren sayfa
    ARTIK DASHBOARD_UI_TOKEN'i gommuyor - once /api/v1/dashboard/auth/login ile
    kullanici adi/parola dogrulanir, donen token sadece tarayicinin
    sessionStorage'inda tutulur ve API cagrilarinda kullanilir."""
    return render_dashboard_html()


@app.post("/api/v1/dashboard/auth/login")
async def login(req: LoginRequest):
    """Auth dependency YOK - girisin kendisi bu uc. Basarili olursa var olan
    kapsami-daraltilmis DASHBOARD_UI_TOKEN doner (yeni bir sir turu icat
    edilmedi). Traefik'teki ki-dashboard-auth BasicAuth katmani (bkz.
    infrastructure/traefik/dynamic/dashboard.yml) bagimsiz/degismeden kalir -
    bu SADECE uygulama-ici login, /dashboard onundeki BasicAuth'un yerini ALMAZ,
    ustune eklenir (ozellikle Traefik'i atlayan dogrudan :5009 erisiminde onemli)."""
    valid = (
        secrets.compare_digest(req.username, settings.DASHBOARD_USERNAME) and
        secrets.compare_digest(req.password, settings.DASHBOARD_PASSWORD)
    )
    if not valid:
        await asyncio.sleep(0.5)  # basit brute-force surtunmesi
        raise HTTPException(status_code=401, detail="Gecersiz kullanici adi veya parola")
    return {"token": settings.DASHBOARD_UI_TOKEN}


@app.get("/api/v1/dashboard/ceo", dependencies=[Depends(verify_api_key)])
async def ceo_dashboard():
    decisions_resp, err = await _safe_get(
        app.state.http, f"{settings.MEMORY_API_URL}/api/v1/memory/retrieve?mem_type=global&scope_key=ceo:decisions&limit=50"
    )
    items = [i["content"] for i in (decisions_resp or {}).get("items", []) if isinstance(i.get("content"), dict)]
    by_status = {}
    for d in items:
        status = d.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "total_decisions": len(items),
        "by_status": by_status,
        "recent": items[:10],
        "degraded": err is not None,
        "errors": [err] if err else [],
    }


@app.get("/api/v1/dashboard/departments", dependencies=[Depends(verify_api_key)])
async def departments_dashboard():
    views = await asyncio.gather(*[_dept_view(app.state.http, d) for d in settings.ACTIVE_DEPARTMENTS])
    return {"departments": list(views)}


@app.get("/api/v1/dashboard/projects", dependencies=[Depends(verify_api_key)])
async def projects_dashboard():
    results = await asyncio.gather(*[
        _safe_get(app.state.http, f"{settings.PROJECTS_API_URL}/api/v1/projects/{p}/report") for p in settings.PROJECTS
    ])
    summaries = []
    for project, (report, err) in zip(settings.PROJECTS, results):
        if report is None:
            summaries.append({"project": project, "status": "unavailable", "degraded": True, "errors": [err] if err else []})
        else:
            summaries.append({
                "project": project,
                "roadmap_items": report.get("roadmap_items", 0),
                "backlog_count": report.get("backlog_count", 0),
                "deliverables_count": report.get("deliverables_count", 0),
                "cost_flagged_count": report.get("cost_flagged_count", 0),
                "degraded": report.get("degraded", False),
            })
    return {"projects": summaries}


@app.get("/api/v1/dashboard/finance", dependencies=[Depends(verify_api_key)])
async def finance_dashboard():
    """NOT: bu panel GERCEK bir para toplami DEGILDIR - Project Manager'in
    /budget ucu (bkz. core/projects/main.py, Phase 6) sadece CFO'nun
    cost_flag=true isaretledigi is sayisini/serbest-metin notunu listeler.
    Yapilandirilmis maliyet alani (orn. tahmini $ tutari) Executive Board'un
    ciktisinda henuz yok."""
    results = await asyncio.gather(*[
        _safe_get(app.state.http, f"{settings.PROJECTS_API_URL}/api/v1/projects/{p}/budget") for p in settings.PROJECTS
    ])
    all_cost_items, errors = [], []
    for project, (budget, err) in zip(settings.PROJECTS, results):
        if err:
            errors.append(err)
            continue
        for item in (budget or {}).get("cost_flagged_items", []):
            all_cost_items.append({"project": project, **item})
    # approval_status yalnizca "published" veya "approval_timeout" olabilir
    # (core/workflow/workflows.py) - yani bu sayac gercekte SU AN bekleyen
    # onaylari DEGIL, SURESI DOLMUS (artik onaylanamayacak) isleri sayar.
    # Gercekten hala RUNNING/onay bekleyen workflow'lar ceo:decisions'da HIC
    # KAYIT uretmiyor (Aethris Phase 8'de bulunan AYNI kok neden) - bu yuzden
    # "su an kac onay bekliyor" burada guvenilir sekilde hesaplanamiyor.
    expired = [i for i in all_cost_items if i.get("approval_status") == "approval_timeout"]
    return {
        "disclaimer": "Bu panel gercek bir para toplami degildir - sadece CFO'nun maliyet-isaretledigi is sayisini/notlarini listeler.",
        "total_cost_flagged_items": len(all_cost_items),
        "expired_approval_count": len(expired),
        "pending_approval_count": None,
        "pending_approval_note": "Su an bekleyen onaylar guvenilir sekilde raporlanamiyor - bilinen kisit, bkz. proje hafizasi (Aethris Phase 8 K1 ile ayni kok neden).",
        "items": all_cost_items,
        "degraded": bool(errors),
        "errors": errors,
    }


@app.get("/api/v1/dashboard/marketing", dependencies=[Depends(verify_api_key)])
async def marketing_dashboard():
    if "marketing" not in settings.ACTIVE_DEPARTMENTS:
        raise HTTPException(status_code=404, detail="Marketing departmani aktif degil")
    (backlog, backlog_err), (deliverables, deliverables_err) = await asyncio.gather(
        _safe_get(app.state.http, f"{settings.DEPARTMENTS_API_URL}/api/v1/departments/marketing/backlog?limit=50"),
        _safe_get(app.state.http, f"{settings.WORKERS_API_URL}/api/v1/workers/marketing/deliverables?limit=50"),
    )
    errors = [e for e in (backlog_err, deliverables_err) if e]
    return {
        "backlog": (backlog or {}).get("items", []),
        "deliverables": (deliverables or {}).get("items", []),
        "degraded": bool(errors),
        "errors": errors,
    }


@app.get("/api/v1/dashboard/chief/{chief}", dependencies=[Depends(verify_api_key)])
async def chief_dashboard(chief: str):
    """Chief-bazli konsolide gorunum: o Chief'e bagli departmanlarin backlog/
    teslimat ozeti + gercek/turetilmis KPI'lar (auto_kpis) + manuel girilmis
    KPI'lar (manual_kpis) + kullanicinin verdigi tam KPI listesi (kpi_catalog).
    auto_kpis SADECE gercekten dogru/yaniltici-olmayan hesaplanabilecegi
    yerlerde doldurulur (CTO: ceo:decisions'tan deployment/basari orani, CFO:
    core/finance ekstre islemleri, CRO: Twenty CRM canli pipeline, COO/CEO:
    dogrudan karsiligi olan tek KPI). Karsiligi olmayan KPI'lar icin sahte
    sayi UYDURULMAZ - manual_kpis'te yoksa UI 'veri kaynagi yok' gosterir."""
    if chief not in CHIEFS:
        raise HTTPException(status_code=404, detail=f"Gecersiz chief: {chief}. Gecerli degerler: {CHIEFS}")

    chief_depts = sorted(d for d, c in settings.DEPARTMENT_TO_CHIEF.items() if c == chief and d in settings.ACTIVE_DEPARTMENTS)
    chief_workflows = {wf for wf, dept in settings.WORKFLOW_TO_DEPARTMENT.items() if dept in chief_depts}

    dept_views, (decisions_data, decisions_err) = await asyncio.gather(
        asyncio.gather(*[_dept_view(app.state.http, d) for d in chief_depts]),
        _safe_get(app.state.http, f"{settings.MEMORY_API_URL}/api/v1/memory/retrieve?mem_type=global&scope_key=ceo:decisions&limit=200"),
    )
    dept_views = list(dept_views)
    decisions_items = [i["content"] for i in (decisions_data or {}).get("items", []) if isinstance(i.get("content"), dict)]
    chief_decisions = [d for d in decisions_items if d.get("workflow") in chief_workflows]

    auto_kpis: dict[str, dict] = {}
    extra_errors: list[str] = []

    if chief == "cto":
        completed = [d for d in chief_decisions if d.get("status") == "completed"]
        failed = [d for d in chief_decisions if d.get("status") == "failed"]
        deploy_completed = [d for d in completed if d.get("workflow") in ("deployment", "development")]
        total = len(completed) + len(failed)
        auto_kpis["deployment_frequency"] = {
            "value": len(deploy_completed), "unit": "count",
            "note": f"son {len(chief_decisions)} kayitlik pencerede deployment/development tamamlanma sayisi (ceo:decisions)",
        }
        if total:
            auto_kpis["change_failure_rate"] = {
                "value": round(len(failed) / total * 100, 1), "unit": "percent",
                "note": "tamamlanan islerin basarisiz olma orani (ceo:decisions)",
            }
        auto_kpis["engineering_velocity"] = {
            "value": sum(d.get("backlog_count", 0) + d.get("deliverables_count", 0) for d in dept_views),
            "unit": "count", "note": "CTO departmanlari backlog+teslimat toplami (proxy)",
        }

    elif chief == "cfo":
        fin_data, fin_err = await _safe_get(app.state.http, f"{settings.FINANCE_API_URL}/api/v1/finance/transactions?limit=500")
        txns = (fin_data or {}).get("transactions", [])
        if txns:
            inflow = sum(t["amount"] for t in txns if isinstance(t.get("amount"), (int, float)) and t["amount"] > 0)
            outflow = sum(t["amount"] for t in txns if isinstance(t.get("amount"), (int, float)) and t["amount"] < 0)
            auto_kpis["revenue"] = {"value": round(inflow, 2), "unit": "currency", "note": f"{len(txns)} ekstre isleminden giris toplami (core/finance)"}
            auto_kpis["burn_rate"] = {"value": round(abs(outflow), 2), "unit": "currency", "note": "ekstre cikis toplami (core/finance)"}
            auto_kpis["cash_flow"] = {"value": round(inflow + outflow, 2), "unit": "currency", "note": "net (giris-cikis, core/finance)"}
        elif fin_err:
            extra_errors.append(fin_err)

    elif chief == "cro":
        twenty_data, twenty_err = await _twenty_query(app.state.http, """
        query { opportunities(first: 200) { edges { node { id name stage amount createdAt } } } }
        """)
        if twenty_data is not None:
            edges = (twenty_data.get("opportunities") or {}).get("edges", [])
            by_stage: dict[str, dict] = {}
            total_amount = 0.0
            for e in edges:
                node = e.get("node", {})
                stage = node.get("stage") or "unknown"
                try:
                    amt = float(node.get("amount") or 0)
                except (TypeError, ValueError):
                    amt = 0.0
                total_amount += amt
                bucket = by_stage.setdefault(stage, {"count": 0, "amount": 0.0})
                bucket["count"] += 1
                bucket["amount"] += amt
            auto_kpis["pipeline_coverage"] = {
                "value": round(total_amount, 2), "unit": "currency",
                "note": f"{len(edges)} acik/kapali firsatin toplam degeri (Twenty CRM, gercek zamanli). "
                        "Win Rate/ARR icin 'won' asamasi henuz dogrulanmadigindan hesaplanmadi, manuel girilebilir.",
            }
            auto_kpis["_stage_breakdown"] = by_stage
        elif twenty_err:
            extra_errors.append(twenty_err)

    elif chief == "coo":
        support = next((d for d in dept_views if d.get("department") == "support"), None)
        if support:
            auto_kpis["support_backlog"] = {"value": support.get("backlog_count", 0), "unit": "count", "note": "support departmani backlog sayisi"}

    elif chief == "ceo":
        completed = [d for d in decisions_items if d.get("status") == "completed"]
        failed = [d for d in decisions_items if d.get("status") == "failed"]
        total = len(completed) + len(failed)
        if total:
            auto_kpis["strategic_initiative_success"] = {
                "value": round(len(completed) / total * 100, 1), "unit": "percent",
                "note": f"{total} karardan basariyla tamamlanma orani (ceo:decisions)",
            }

    manual_kpis, manual_err = await _get_manual_kpis(app.state.http, chief)

    return {
        "chief": chief,
        "label": CHIEF_LABELS[chief],
        "departments": dept_views,
        "kpi_catalog": [{"key": k, "label": l} for k, l in CHIEF_KPI_CATALOG.get(chief, [])],
        "auto_kpis": auto_kpis,
        "manual_kpis": manual_kpis,
        "degraded": bool(extra_errors) or bool(manual_err) or bool(decisions_err),
        "errors": extra_errors + ([decisions_err] if decisions_err else []) + ([manual_err] if manual_err else []),
    }


@app.post("/api/v1/dashboard/metrics/{chief}/{kpi_key}", dependencies=[Depends(verify_master_key)])
async def record_metric(chief: str, kpi_key: str, req: MetricEntryRequest):
    """Otomatik veri kaynagi olmayan KPI'lar (ARR/MRR/CAC/eNPS gibi is verisi
    gerektirenler) icin manuel giris - Invoice Ninja/anket gibi entegrasyonlar
    baglanana kadar gecici kalici depo. DISPATCH ile ayni yetki seviyesi
    (verify_master_key) - salt-okunur UI token'i yazma yapamaz."""
    if chief not in CHIEFS:
        raise HTTPException(status_code=404, detail=f"Gecersiz chief: {chief}. Gecerli degerler: {CHIEFS}")
    valid_keys = {k for k, _ in CHIEF_KPI_CATALOG.get(chief, [])}
    if kpi_key not in valid_keys:
        raise HTTPException(status_code=422, detail=f"Gecersiz kpi_key: {kpi_key}. Gecerli degerler: {sorted(valid_keys)}")
    content = {"kpi_key": kpi_key, "value": req.value, "note": req.note, "entered_at": datetime.now(timezone.utc).isoformat()}
    try:
        resp = await app.state.http.post(
            f"{settings.MEMORY_API_URL}/api/v1/memory/store",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json={"mem_type": "global", "scope_key": f"kpi:{chief}", "content": content},
            timeout=15.0,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Memory'e yazilamadi: {e}")
    return {"status": "ok", "chief": chief, "kpi_key": kpi_key, "value": req.value}


@app.get("/api/v1/dashboard/system", dependencies=[Depends(verify_api_key)])
async def system_dashboard():
    async def _check(name: str, url: str) -> dict:
        health, err = await _safe_get(app.state.http, f"{url}/health", timeout=5.0)
        status = (health or {}).get("status", "unreachable") if err is None else "unreachable"
        return {"service": name, "status": status, "detail": health}

    results = await asyncio.gather(*[_check(name, url) for name, url in ALL_SERVICES.items()])
    healthy_count = sum(1 for r in results if r["status"] == "ok")
    return {
        "services": list(results),
        "healthy_count": healthy_count,
        "total_count": len(ALL_SERVICES),
        "overall_status": "ok" if healthy_count == len(ALL_SERVICES) else "degraded",
    }


@app.get("/api/v1/dashboard/integrations", dependencies=[Depends(verify_api_key)])
async def integrations_dashboard():
    """Composio uzerinden baglanan tum toolkit/app'lerin (Gmail, Slack, GitHub, vb.)
    ozet gorunumu - core/composio servisinin periyodik senkronladigi cache'i proxy'ler."""
    data, err = await _safe_get(app.state.http, f"{settings.COMPOSIO_API_URL}/api/v1/composio/connections")
    if err is not None:
        return {"total": 0, "by_toolkit": {}, "accounts": [], "error": err}
    return data


@app.get("/api/v1/dashboard/workflows", dependencies=[Depends(verify_api_key)])
async def list_dispatchable_workflows():
    """Dispatch formunun dropdown'ini doldurmak icin - salt-okunur, UI token yeterli."""
    return {"workflows": DISPATCHABLE_WORKFLOWS}


@app.post("/api/v1/dashboard/dispatch", dependencies=[Depends(verify_master_key)])
async def dispatch_task(req: DispatchRequest):
    """Herhangi bir Chief/departmana GERCEK bir gorev dispatch eder - core/ceo'nun
    zaten var olan /api/v1/ceo/dispatch ucuna proxy yapar (2026-07-16, kullanicinin
    "worker'lar hazir gorev alabiliyor olsun" talebiyle eklendi). SADECE tam
    INTERNAL_API_KEY ile cagrilabilir (bkz. verify_master_key)."""
    if req.workflow not in DISPATCHABLE_WORKFLOWS:
        raise HTTPException(status_code=422, detail=f"Gecersiz workflow: {req.workflow}. Gecerli degerler: {DISPATCHABLE_WORKFLOWS}")
    try:
        resp = await app.state.http.post(
            f"{settings.CEO_API_URL}/api/v1/ceo/dispatch",
            headers={
                "Authorization": f"Bearer {settings.INTERNAL_API_KEY}",
                "Idempotency-Key": f"dashboard-ui-{uuid.uuid4()}",
            },
            json=req.model_dump(),
            timeout=15.0,
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"CEO servisine erisilemedi: {e}")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@app.get("/health")
async def health():
    try:
        resp = await app.state.http.get(f"{settings.MEMORY_API_URL}/health", timeout=5.0)
        memory_ok = resp.status_code == 200
    except Exception:
        memory_ok = False
    return {"status": "ok" if memory_ok else "degraded", "checks": {"memory": memory_ok}}
