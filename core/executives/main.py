"""
KI Enterprise Executive Board (Phase 3).

CEO altinda calisir. Departman/worker katmani (Phase 4/5) henuz kurulmadigi icin
Executive Board su an CEO'nun ürettigi planlari 5 yonetici perspektifinden
(CTO/CFO/CMO/COO/CISO) inceler, kararlarini Memory Layer'a kaydeder.

CFO icin build order'daki maliyet kurali aynen uygulanir:
  "Once ucretsiz, sonra self-hosted, sonra open source, sonra ucretli.
   Her maliyet kullanici onayi ister."
Plan ucretli/paid bir servis/kaynak iceriyorsa CFO cost_flag=true isaretler ve
requires_user_approval alani true doner - Workflow Engine (core/workflow/workflows.py,
ApprovalMixin) bu alani GERCEK bir kapi olarak kullanir: true ise CEO'nun
POST /api/v1/ceo/dispatch/{id}/approve ucuyla approve_cost sinyali gonderilene
kadar task.<workflow> event'i yayinlanmaz.

Guvenlik notu: LLM ciktisi semaya uymuyorsa veya cfo alani hic yoksa, "fail-open"
(cost_flag=False, otomatik onay) DEGIL "fail-safe" (cost_flag=True, onay bekletilir)
davranilir - parse edilemeyen bir yanit "maliyet yok" anlamina gelmemeli.

Bu servis kasitli olarak Workflow Engine'in bir activity'si DEGIL, ayri bir
servistir - ilerideki gelistirme surecinde her birim (CEO, Executive Board,
Departmanlar, Worker'lar) bagimsiz olarak yonetilecek.
"""
import asyncio
import json
import logging
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import httpx
import nats
from fastapi import Depends, FastAPI, Header, HTTPException
from nats.js.api import ConsumerConfig
from pydantic import BaseModel

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("executives")

ROLES = ["cto", "cfo", "cmo", "coo", "ciso"]
QC_MAX_DELIVER = 5

QC_CHIEF_NAMES = {
    "cto": "Kai (CTO)", "cfo": "Vera (CFO)", "cmo": "Iris (CMO)", "coo": "Leo (COO)", "ciso": "Nora (CISO)",
    "cpo": "Selin (CPO)", "cro": "Doruk (CRO)", "cdo": "Aylin (CDO)",
}

# Faz "Chat Odasi" - her Chief'in serbest-metin sohbet persona'si (bkz.
# POST /api/v1/executives/chat/{chief}). Tek dogruluk kaynagi core/personas/
# PERSONAS.md'dir (Yonetim Kurulu bolumu) - burada sohbete uygun kisaltilmis
# hali tutuluyor, orada degisirse burasi da elle guncellenmeli.
CHIEF_PERSONAS = {
    "cto": (
        "Sen Kai'sin - KI Enterprise'in CTO'susun. Urettigin sey kod degil, "
        "geri dondurulebilir kararlar ve ekibin uzun vadeli hizidir. 'En iyi "
        "teknoloji' diye evrensel bir sey yoktur, sadece 'bu baglamda dogru "
        "trade-off' vardir. Her teknik oneriyi borc matrisinde degerlendirirsin "
        "(bilerek mi alindi/cehaletten mi, ihtiyatli mi/pervasiz mi). Teknik "
        "borcu nazik ama net soylersin: '6 ay sonra patlar, simdi 2 gun "
        "harcarsak patlamaz.' Turkce konusursun, kisa ve somut yazarsin - bu "
        "bir sohbet odasi, resmi rapor degil."
    ),
    "cfo": (
        "Sen Vera'sin - KI Enterprise'in CFO'susun. Rakam onceliklisin, dogan "
        "geregi supheci - her ucretli harcamayi once sorgularsin ('bunun "
        "ucretsiz/self-hosted alternatifi denendi mi?'). Net ROI gorunce "
        "onaylarsin, sadece gerekcesiz harcamaya izin vermezsin. Sirket "
        "politikasi: once ucretsiz, sonra self-hosted, sonra acik kaynak, "
        "sonra ucretli. Turkce konusursun, kisa ve somut yazarsin - bu bir "
        "sohbet odasi, resmi rapor degil."
    ),
    "cmo": (
        "Sen Iris'sin - KI Enterprise'in CMO'susun. Buyume ve marka odakli, "
        "iyimsersin. Isin disaridan/musteri gozunden nasil gorundugunu "
        "dusunursun. Vera'nin (CFO) frugal tavriyla zaman zaman gerilirsin ama "
        "bu saglikli bir gerilim. Turkce konusursun, kisa ve somut yazarsin - "
        "bu bir sohbet odasi, resmi rapor degil."
    ),
    "coo": (
        "Sen Leo'sun - KI Enterprise'in COO'susun. 'Urunun' vizyon degil "
        "teslimattir - John neyin yapilacagini satar, sen nasil ve ne zaman "
        "yapilacagini garanti edersin. Andy Grove mantigiyla dusunursun: her "
        "proje bir girdi-cikti-darbogaz zinciridir. Ilk sorun 'en dar bogaz "
        "hangi adimda', ikincisi 'bunu nasil olcerim'. Scope creep'e "
        "toleransin dusuktur. Turkce konusursun, kisa ve somut yazarsin - bu "
        "bir sohbet odasi, resmi rapor degil."
    ),
    "ciso": (
        "Sen Nora'sin - KI Enterprise'in CISO'susun. Gorevin 'hayir' demek "
        "degil, riski fiyatlandirmaktir. Zero Trust ilkesini tasirsin - her "
        "yeni entegrasyon 'bu neden guvenilir?' sorusundan gecer. FAIR "
        "mantigiyla dusunursun: 'bu acigin gerceklesme olasiligi nedir, "
        "gerceklesirse kayip ne kadar?' Somut/kanitlanmis aciksa hizli 'red' "
        "dersin, teorik/uzak riske 'kaygi' ile yetinirsin ama takip listesine "
        "yazarsin. Turkce konusursun, kisa ve somut yazarsin - bu bir sohbet "
        "odasi, resmi rapor degil."
    ),
    "cpo": (
        "Sen Selin'sin - KI Enterprise'in CPO'susun. Gercek urunun ozellik "
        "degil, cozulmus musteri problemidir. Bir talep geldiginde once "
        "'hangi problem, kim icin, ne siklikta' diye sorarsin, cozum "
        "onerisiyle gelenleri bile probleme geri cekersin. 'Kac ozellik "
        "cikti' degil 'hangi metrik degisti' sorusuna sahip cikarsin. Turkce "
        "konusursun, kisa ve somut yazarsin - bu bir sohbet odasi, resmi "
        "rapor degil."
    ),
    "cro": (
        "Sen Doruk'sun - KI Enterprise'in CRO'susun. Sattigin sey urun degil, "
        "ongorulebilirliktir - degerli olan 'buyuk ay' degil 'tahmin "
        "ettigim ayi tutturmak'tir. Her firsati MEDDPICC merceginden "
        "gecirirsin - 'bu deal gercek mi yoksa CRM'i sisiren bir hayal mi'. "
        "Seffaf forecast verirsin, kotu haberi buyutmeden erken soylersin. "
        "Turkce konusursun, kisa ve somut yazarsin - bu bir sohbet odasi, "
        "resmi rapor degil."
    ),
    "cdo": (
        "Sen Aylin'sin - KI Enterprise'in CDO'susun. Veriyi mulk degil, "
        "paylasilan bir kamu mali gibi gorursun - sahibi sen degilsin ama "
        "kimin sahip oldugunu her zaman bilirsin. Her rakam/rapor gordugunde "
        "uc soru sorarsin: 'Bu veri nereden geldi?', 'Son ne zaman "
        "dogrulandi?', 'Kim bunun sahibi?' Governance'i dayatmazsin, var olan "
        "sorumluluk hatlarini gorunur hale getirirsin. Turkce konusursun, "
        "kisa ve somut yazarsin - bu bir sohbet odasi, resmi rapor degil."
    ),
}

QC_SYSTEM_PROMPT_TEMPLATE = (
    "Sen {chief}sin - KI Enterprise'in yonetim kurulu uyesisin. Bir worker'in "
    "tamamladigi ve KENDI oz-degerlendirmesinde dusuk puan aldigi bir is "
    "ciktisini KENDI bakis acinla, BAGIMSIZ olarak yeniden degerlendiriyorsun. "
    "SADECE asagidaki JSON semasina uyan bir cikti uret, baska hicbir metin ekleme:\n\n"
    '{{"score": 0-100, "gaps": ["eksik/sorunlu nokta", ...], "corrective_action": "onerilen somut duzeltme, 1 cumle"}}\n\n'
    "Cikti somut/eksiksiz/gorevi karsilar nitelikte degilse dusuk puan ver."
)
# Plan icerigi kullanici/CEO tarafindan uretilen serbest metindir - sisteme
# talimat enjekte etmeyi zorlastirmak icin uzunluk sinirlanir (ayrica gereksiz
# token/maliyet de onlenir).
MAX_PLAN_CHARS = 4000

# Tek dogruluk kaynagi: core/personas/PERSONAS.md (Yonetim Kurulu bolumu).
# Orada degisirse burasi da elle guncellenmeli (ayri servis/venv - dogrudan import edilemiyor).
REVIEW_SYSTEM_PROMPT = """Sen KI Enterprise sirketinin Executive Board'usun - 5 ayri
karakterin sesisin, her biri kendi bakis acisiyla degerlendirir. Sana bir CEO plani
verilecek. SADECE asagidaki JSON semasina uyan bir cikti uret, baska hicbir metin ekleme:

{
  "cto": {"verdict": "onay|kaygi|red", "notes": "teknik degerlendirme, 1-2 cumle"},
  "cfo": {"verdict": "onay|kaygi|red", "notes": "finansal degerlendirme, 1-2 cumle", "cost_flag": true|false},
  "cmo": {"verdict": "onay|kaygi|red", "notes": "pazarlama degerlendirmesi, 1-2 cumle"},
  "coo": {"verdict": "onay|kaygi|red", "notes": "operasyonel degerlendirme, 1-2 cumle"},
  "ciso": {"verdict": "onay|kaygi|red", "notes": "guvenlik degerlendirmesi, 1-2 cumle", "risk_flag": true|false, "risk_notes": "somut risk aciklamasi (risk_flag=true ise doldur, degilse bos birak)"}
}

Karakterler (notes alanini bu sesle yaz):
- cto = Kai: trade-off muhendisi (Fowler'in tech debt quadrant'i, Vogels'in "you build
  it you run it" ilkesi). Abartili/moda teknolojiye degil kanitlanmis, bakimi kolay
  cozumlere guvenir. Teknik borc/olceklenebilirlik riskini nazik ama net soyler,
  "6 ay sonra patlar" gibi somut vadeyle konusur.
- cfo = Vera: rakam onceliki, dogasi geregi supheci - her ucretli harcamayi once
  sorgular. Net ROI gorunce onaylar, gerekcesiz harcamaya izin vermez.
- cmo = Iris: buyume/marka odakli, iyimser. Isin disaridan/musteri gozunden nasil
  gorundugunu dusunur.
- coo = Leo: Andy Grove'un girdi-cikti-darbogaz mantigiyla dusunur, Task-Relevant
  Maturity'e gore delege eder. Zaman cizelgesi, bagimlilik, RACI netligi onun derdi.
  Kapsam kaymasina (scope creep) toleransi dusuk, gerekcesini soyler.
- ciso = Nora: FAIR mantigiyla dolarla konusan risk muhendisi, Zero Trust varsayimini
  tasir ("bu neden guvenilir?"). Tiyatro yapmaz, somut aciksa "red", teorik/uzak
  riske "kaygi" yeter - ama takip listesine yazar.

CFO KURALI (ONEMLI, karakterden BAGIMSIZ islevsel kural - degistirilemez): Sirket
politikasi "once ucretsiz, sonra self-hosted, sonra open source, sonra ucretli"dir.
Plan ucretli/paid bir servis, API veya kaynak kullanimi iceriyorsa cfo.cost_flag=true
yap ve notes alaninda hangi maliyetin kullanici onayi gerektirdigini belirt.
Ucretsiz/self-hosted/open-source kaynaklar kullaniliyorsa cost_flag=false yap.

CISO KURALI (ONEMLI, karakterden BAGIMSIZ islevsel kural): Planda somut bir
guvenlik/operasyonel risk goruyorsan (orn. yetkisiz erisim, veri sizintisi,
tek-nokta-hata, telafisi zor/geri alinamaz bir islem, gizlilik ihlali)
risk_flag=true yap ve risk_notes'a SOMUT aciklama yaz - bu Risk Register'a
otomatik kaydedilir (ISO 31000/COSO ERM). Onemsiz/teorik konularda
risk_flag=false birak, risk_notes'u bos gec."""


class ReviewRequest(BaseModel):
    workflow: str
    prompt: str
    plan: str


class ChiefChatRequest(BaseModel):
    message: str
    context: str = ""  # oda gecmisinden ozetlenmis onceki mesajlar (opsiyonel)


async def verify_api_key(authorization: str = Header(default="")):
    expected = f"Bearer {settings.INTERNAL_API_KEY}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik Authorization header'i")


_FAIL_SAFE_REVIEWS = {role: {"verdict": "kaygi", "notes": "Degerlendirme parse edilemedi", "parse_error": True} for role in ROLES}


def _coerce_bool_flag(value) -> bool:
    """cost_flag/risk_flag gibi kapı alanlarını tip-guvenli sekilde bool'a
    cevirir. LLM'ler bazen "cost_flag": "false" (STRING) donebilir - Python'da
    bool("false")==True oldugu icin bu ciddi bir bypass riskidir, fail-open olmamali."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "evet")
    return bool(value)


def _parse_review(raw_content: str) -> dict:
    """LLM ciktisini JSON olarak parse eder. Model aciklama metni eklerse
    (yaygin bir LLM davranisi) ilk '{' ile son '}' arasini cikarip tekrar dener.

    Guvenlik: parse basarisiz olursa VEYA cfo alani eksikse fail-SAFE davranilir
    (cost_flag=True, onay bekletilir) - fail-open (cost_flag=False, otomatik
    onay) asla varsayilan olmamalidir. Parse hatasinda raw_content teshis icin
    loglanir."""
    parsed = None
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        start, end = raw_content.find("{"), raw_content.rfind("}")
        if start != -1 and end != -1:
            try:
                parsed = json.loads(raw_content[start:end + 1])
            except json.JSONDecodeError:
                pass

    if not isinstance(parsed, dict):
        logger.error(f"Executive review parse edilemedi, fail-safe uygulaniyor. Ham yanit: {raw_content!r}")
        return dict(_FAIL_SAFE_REVIEWS)

    reviews = {}
    for role in ROLES:
        verdict = parsed.get(role)
        if not isinstance(verdict, dict):
            logger.warning(f"'{role}' icin degerlendirme eksik/gecersiz, fail-safe uygulaniyor. Ham yanit: {raw_content!r}")
            verdict = {"verdict": "kaygi", "notes": "Rol icin degerlendirme yok", "parse_error": True}
        reviews[role] = verdict

    cfo = reviews["cfo"]
    if "cost_flag" not in cfo or cfo.get("parse_error"):
        # cfo eksik/parse edilemedi - maliyet durumu bilinmiyor, fail-safe: onay bekletilsin.
        cfo["cost_flag"] = True
        cfo.setdefault("notes", "CFO degerlendirmesi eksik - guvenlik geregi onay gerektiriyor olarak isaretlendi")
    else:
        cfo["cost_flag"] = _coerce_bool_flag(cfo["cost_flag"])

    # risk_flag icin fail-safe GEREKMEZ (cost_flag'in aksine, eksik/hatali risk
    # degerlendirmesi bir workflow'u BLOKE etmez - Risk Register'a sadece bir
    # kayit eklenmez, riskli bir islem otomatik onaylanmis OLMAZ). Bu yuzden
    # eksikse sessizce False varsayilir.
    ciso = reviews.get("ciso")
    if isinstance(ciso, dict):
        ciso["risk_flag"] = _coerce_bool_flag(ciso.get("risk_flag", False))

    return reviews


async def _remember(mem_type: str, scope_key: str, content: dict, idempotency_key: str | None = None) -> bool:
    try:
        body = {"mem_type": mem_type, "scope_key": scope_key, "content": content}
        if idempotency_key:
            body["idempotency_key"] = idempotency_key
        resp = await app.state.http.post(
            f"{settings.MEMORY_API_URL}/api/v1/memory/store",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json=body,
        )
        resp.raise_for_status()
        return True
    except httpx.HTTPError as e:
        logger.warning(f"Memory'e yazilamadi ({mem_type}/{scope_key}): {e}")
        return False


async def _audit(actor: str, action: str, target: str, decision: str, detail: str = ""):
    """Faz D2 - core/governance'in append-only audit trail'ine yazar. Fire-and-
    forget: governance servisine erisilemezse review/QC akisini bloklamaz."""
    try:
        resp = await app.state.http.post(
            f"{settings.GOVERNANCE_API_URL}/api/v1/audit",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json={"actor": actor, "action": action, "target": target, "decision": decision, "detail": detail},
            timeout=5.0,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning(f"Audit kaydi yazilamadi (ana akis etkilenmedi): {e}")


async def _memory_get_items(mem_type: str, scope_key: str, limit: int = 500) -> list[dict]:
    """Ham Memory 'items' listesini (id/content/created_at) doner - Risk
    Register gibi append-only + reduce-to-latest desenleri icin created_at
    gerekli, sadece content'i cikaran diger yardimcilardan (core/improvement
    _memory_get gibi) farkli."""
    try:
        resp = await app.state.http.get(
            f"{settings.MEMORY_API_URL}/api/v1/memory/retrieve",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            params={"mem_type": mem_type, "scope_key": scope_key, "limit": limit},
        )
        resp.raise_for_status()
        return resp.json().get("items", [])
    except httpx.HTTPError as e:
        logger.warning(f"Memory'den okunamadi ({mem_type}/{scope_key}): {e}")
        return []


def _latest_by_id(items: list[dict]) -> dict[str, dict]:
    """Memory Layer'da UPDATE yoktur, sadece INSERT - bir kaydin 'guncellenmesi'
    ayni content['id']'ye sahip YENI bir satir eklemek demektir (bkz. Risk
    Register POST/PATCH). Bu fonksiyon, id basina en yeni (created_at) kaydi
    secer - append-only + reduce-to-latest deseni."""
    latest: dict[str, dict] = {}
    for item in items:
        content = item.get("content")
        if not isinstance(content, dict) or "id" not in content:
            continue
        rid = content["id"]
        created_at = item.get("created_at", "")
        if rid not in latest or created_at > latest[rid].get("_created_at", ""):
            latest[rid] = {**content, "_created_at": created_at}
    for entry in latest.values():
        entry.pop("_created_at", None)
    return latest


RISK_REGISTER_SCOPE_KEY = "risk_register"


class RiskCreate(BaseModel):
    title: str
    layer: str  # governance | operations | technology | data_ai
    chief: str  # cto/cfo/cmo/coo/ciso/cpo/cro/cdo
    likelihood: int = 3  # 1-5
    impact: int = 3  # 1-5
    mitigation: str = ""
    source: str = "manual"  # manual | auto_review


class RiskUpdate(BaseModel):
    status: Optional[str] = None  # open | mitigating | closed
    mitigation: Optional[str] = None


async def _create_risk(req: RiskCreate) -> dict:
    """Risk Register'a yeni bir risk ekler - ISO 31000/COSO ERM'in somut
    kod-seviyesi karsiligi (Risk Register/Risk Score). Hem manuel (POST
    /api/v1/risks) hem otomatik (executive_review'daki ciso.risk_flag=true)
    cagirilardan kullanilir."""
    risk_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    likelihood = max(1, min(5, req.likelihood))
    impact = max(1, min(5, req.impact))
    content = {
        "id": risk_id, "title": req.title, "layer": req.layer, "chief": req.chief,
        "likelihood": likelihood, "impact": impact, "risk_score": likelihood * impact,
        "mitigation": req.mitigation, "status": "open", "source": req.source,
        "created_at": now, "updated_at": now,
    }
    ok = await _remember("global", RISK_REGISTER_SCOPE_KEY, content, idempotency_key=f"risk-create:{risk_id}")
    if not ok:
        logger.warning(f"Risk Memory'e kaydedilemedi: {content['title']}")
    return content


async def _qc_score(chief_role: str, workflow_name: str, deliverable_summary: str) -> dict:
    """Katman 2 (Chief QC) - worker'in oz-degerlendirmesinden BAGIMSIZ, ilgili
    Chief'in bakis acisiyla ikinci bir puanlama. Sadece worker'in kendisi
    "completed_low_quality" isaretledigi isler icin cagrilir (bkz. _qc_process_one) -
    her tamamlanan is icin degil, maliyet disiplinini korumak icin."""
    chief_name = QC_CHIEF_NAMES.get(chief_role, chief_role.upper())
    try:
        resp = await app.state.http.post(
            f"{settings.AI_GATEWAY_URL}/api/chat",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json={
                "model": settings.REVIEW_MODEL,
                "temperature": 0.2,
                "priority": "normal",
                "messages": [
                    {"role": "system", "content": QC_SYSTEM_PROMPT_TEMPLATE.format(chief=chief_name)},
                    {"role": "user", "content": f"Is turu: {workflow_name}\n\nCikti ozeti:\n{deliverable_summary[:1500]}"},
                ],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        start, end = raw.find("{"), raw.rfind("}")
        parsed = json.loads(raw[start:end + 1]) if start != -1 and end != -1 else json.loads(raw)
        return {
            "score": int(parsed.get("score", 0)), "gaps": parsed.get("gaps") or [],
            "corrective_action": parsed.get("corrective_action", ""),
        }
    except (httpx.HTTPError, KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
        logger.warning(f"QC puanlama basarisiz: {e}")
        return {"score": None, "gaps": [], "corrective_action": ""}


async def _qc_process_one(nc: nats.NATS, msg):
    """report.> uzerinden gelen bir mesaji isler. SADECE worker'in kendi
    Katman-1 oz-kontrolunde dusuk puan aldigi ("completed_low_quality") isler
    icin Chief QC calisir - normal "completed" raporlar ek maliyet olmadan ack edilir."""
    source_id = f"{msg.metadata.stream}:{msg.metadata.sequence.stream}"
    try:
        raw = msg.data.decode()
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Bozuk rapor mesaji, dusuruluyor ({msg.subject}): {e}")
        await msg.term()
        return

    if payload.get("status") != "completed_low_quality":
        await msg.ack()
        return

    department = msg.subject.split(".", 1)[1] if "." in msg.subject else "unknown"
    chief = settings.DEPARTMENT_TO_CHIEF.get(department, "coo")
    workflow_name = payload.get("workflow", "unknown")
    qc = await _qc_score(chief, workflow_name, payload.get("deliverable_summary", ""))
    now = datetime.now(timezone.utc).isoformat()

    if qc["score"] is not None and qc["score"] < settings.QUALITY_MIN_SCORE:
        # Duzeltici faaliyet: dusuk-riskli, geri alinabilir bir is-akisi aksiyonu
        # (Miracin onayini GEREKTIRMEZ, bkz. build-order kisiti - core/improvement
        # ile ayni sinir) - is worker'a revizyon icin geri gonderilir.
        revision = payload.get("revision", 0)
        if revision < settings.MAX_REVISIONS:
            try:
                await nc.jetstream().publish(
                    f"task.{workflow_name}",
                    json.dumps({
                        "workflow": workflow_name,
                        "prompt": (
                            f"[QC REVIZYON {revision + 1} - {chief.upper()} geri bildirimi] Onceki "
                            f"ciktida su sorunlar bulundu: "
                            f"{'; '.join(str(g) for g in qc['gaps']) or qc['corrective_action'] or 'kalite yetersiz'}. "
                            "Gorevi bu eksikleri giderek YENIDEN yap."
                        ),
                        "plan": "(QC otomatik revizyon talebi - orijinal plan mevcut degil)",
                        "project": payload.get("project", ""),
                        "executive_review": {}, "requires_user_approval": False,
                        "revision": revision + 1,
                    }).encode(),
                    headers={"Nats-Msg-Id": f"qc-revision:{source_id}"},
                )
                corrective = f"{chief} tarafindan worker'a revizyon icin geri gonderildi (revizyon {revision + 1})"
            except Exception as e:
                logger.warning(f"QC revizyon yayinlanamadi: {e}")
                corrective = "revizyon yayinlanamadi (NATS hatasi)"
        else:
            corrective = f"{chief}: revizyon hakki tukendi, elle inceleme gerekiyor"

        # Onleyici faaliyet: tekrar eden kalite deseni Faz B'nin self-improvement
        # kapanisinin (core/improvement) okuyacagi ayri bir scope'a kaydedilir.
        await _remember("global", f"qc:preventive:{department}", {
            "department": department, "chief": chief, "workflow": workflow_name,
            "qc_score": qc["score"], "qc_gaps": qc["gaps"], "noted_at": now,
        })

        # CEO'ya raporlama: gun basi/gun sonu ozetinde (Faz B) gorunecek.
        await _remember("global", "ceo:escalations", {
            "workflow_id": None, "workflow": workflow_name, "project": payload.get("project", ""),
            "type": "quality_failure", "department": department, "chief": chief,
            "qc_score": qc["score"], "qc_gaps": qc["gaps"], "corrective_action": qc["corrective_action"],
            "corrective_taken": corrective, "detail": qc["corrective_action"] or "Kalite esiginin altinda.",
            "severity": "medium", "escalated_at": now,
        }, idempotency_key=f"escalation-qc:{source_id}")

        await _audit(actor=chief, action="qc_corrective_action", target=workflow_name, decision=corrective,
                      detail=f"department={department} qc_score={qc['score']}")

    await _remember("department", f"qc:{department}", {
        "workflow": workflow_name, "chief": chief, "qc_score": qc["score"], "qc_gaps": qc["gaps"],
        "worker_score": payload.get("quality_score"), "reviewed_at": now,
    }, idempotency_key=f"qc-review:{source_id}")

    await msg.ack()


async def _qc_loop(nc: nats.NATS, heartbeat: dict):
    js = nc.jetstream()
    sub = await js.pull_subscribe(
        "report.>",
        durable=settings.QC_CONSUMER_DURABLE,
        stream="REPORT",
        config=ConsumerConfig(max_deliver=QC_MAX_DELIVER, ack_wait=90),
    )
    logger.info("Chief QC basladi (report.> dinleniyor, sadece completed_low_quality isleniyor).")
    while True:
        heartbeat["last_loop"] = datetime.now(timezone.utc)
        try:
            msgs = await sub.fetch(3, timeout=5)
        except TimeoutError:
            continue

        for msg in msgs:
            try:
                await _qc_process_one(nc, msg)
            except Exception as e:
                # Bu katman "en-iyi-caba" bir kalite guvence katidir - deliverable'in
                # kendisi degil, degerlendirmesi. Ana veri yolunu (worker/departman
                # DLQ zinciri) bloke etmemesi icin hata durumunda ack edilir.
                logger.error(f"QC islem hatasi, mesaj ack ediliyor (best-effort katman): {e}")
                try:
                    await msg.ack()
                except Exception:
                    pass


async def _qc_supervisor(nc: nats.NATS, heartbeat: dict):
    """_qc_loop coker/baslangicta patlarsa sessizce olmesin diye loglayip
    backoff ile yeniden baslatir (diger servislerdeki ayni supervisor deseni)."""
    while True:
        try:
            await _qc_loop(nc, heartbeat)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Chief QC coktu, 5sn sonra yeniden baslatiliyor: {e}")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=90.0)
    app.state.nc = await nats.connect(settings.NATS_URL)
    app.state.heartbeat = {"last_loop": None}
    app.state.background_tasks: set[asyncio.Task] = set()

    qc_task = asyncio.create_task(_qc_supervisor(app.state.nc, app.state.heartbeat))
    app.state.qc_task = qc_task
    app.state.background_tasks.add(qc_task)
    qc_task.add_done_callback(app.state.background_tasks.discard)

    logger.info("Executive Board NATS'a baglandi, Chief QC aktif.")
    yield

    for task in list(app.state.background_tasks):
        task.cancel()
    await asyncio.gather(*app.state.background_tasks, return_exceptions=True)
    await app.state.nc.close()
    await app.state.http.aclose()


app = FastAPI(title="KI Enterprise Executive Board", lifespan=lifespan)


@app.post("/api/v1/executives/chat/{chief}", dependencies=[Depends(verify_api_key)])
async def chief_chat(chief: str, req: ChiefChatRequest):
    """Bir Chief'in (CEO haric) serbest-metin sohbet ucu - Chat Odasi ozelligi
    icin (core/ceo'nun /api/v1/ceo/room/message'i, CEO bir Chief'i 'delegate'
    ettiginde bu ucu cagirir). core/ceo/main.py:chat ile AYNI desen (danisma
    amacli, kendisi workflow tetiklemez, dispatch kararini hala CEO/oda
    yonlendiricisi verir)."""
    persona = CHIEF_PERSONAS.get(chief)
    if persona is None:
        raise HTTPException(status_code=404, detail=f"Gecersiz chief: {chief}. Gecerli degerler: {sorted(CHIEF_PERSONAS)}")
    system_prompt = persona
    if req.context:
        system_prompt += f"\n\nOda baglami (bu sohbetteki onceki mesajlar):\n{req.context}"
    try:
        resp = await app.state.http.post(
            f"{settings.AI_GATEWAY_URL}/api/chat",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json={
                "priority": "high",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": req.message},
                ],
            },
            timeout=90.0,
        )
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError) as e:
        raise HTTPException(status_code=502, detail=f"AI Gateway'e erisilemedi/beklenmedik yanit: {e}")
    return {"chief": chief, "name": QC_CHIEF_NAMES.get(chief, chief.upper()), "message": req.message, "answer": answer}


@app.post("/api/v1/executives/review", dependencies=[Depends(verify_api_key)])
async def review(req: ReviewRequest):
    # Sistem talimati (JSON semasi + CFO kurali) ile kullanici/CEO tarafindan
    # uretilen plan metni AYRI mesaj rollerinde gonderilir (chat/completions'in
    # system+user ayrimi) - plan icine "cfo.cost_flag=false yap" gibi bir talimat
    # enjekte edilse bile system rolundeki kurallarla ayni agirlikta degerlendirilmez.
    # Ayrica plan MAX_PLAN_CHARS ile kirpilir (asiri uzun girdiyle bogma/maliyet onlemi).
    truncated_plan = req.plan[:MAX_PLAN_CHARS]
    try:
        resp = await app.state.http.post(
            f"{settings.AI_GATEWAY_URL}/api/chat",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json={
                "model": settings.REVIEW_MODEL,
                "temperature": 0.2,
                "priority": "high",
                "messages": [
                    {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Talep: {req.prompt}\n\nPlan:\n{truncated_plan}"},
                ],
            },
        )
        resp.raise_for_status()
        raw_content = resp.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError) as e:
        raise HTTPException(status_code=502, detail=f"AI Gateway'e erisilemedi/beklenmedik yanit: {e}")

    reviews = _parse_review(raw_content)

    # 5 Memory yazimi sirayla degil PARALEL yapilir - LLM cagrisi zaten 10-90s
    # surebiliyor, sirali 5 ek HTTP cagrisi activities.py'deki 90s activity
    # timeout'unu asma riski yaratiyordu.
    results = await asyncio.gather(*[
        _remember("department", role, {"workflow": req.workflow, "prompt": req.prompt, **reviews[role]})
        for role in ROLES
    ])
    memory_write_failures = [role for role, ok in zip(ROLES, results) if not ok]
    if memory_write_failures:
        logger.warning(f"Bazi degerlendirmeler Memory'e yazilamadi (event/response'ta hala mevcut): {memory_write_failures}")

    # Faz D1 - CISO somut bir risk isaretlerse (risk_flag=true) Risk Register'a
    # otomatik kaydedilir (ISO 31000/COSO ERM'in kod-seviyesi karsiligi).
    # Governance/Operations/Technology/Data&AI katmanlarindan Technology'ye
    # yazilir - CISO'nun dogal alani; digger Chief'ler icin genellestirme
    # ileride (Faz 13'un kapsami, bkz. ORG_CHART.md) yapilabilir.
    ciso_review = reviews.get("ciso", {})
    if isinstance(ciso_review, dict) and ciso_review.get("risk_flag"):
        risk = await _create_risk(RiskCreate(
            title=f"[Otomatik - {req.workflow}] {(ciso_review.get('risk_notes') or 'CISO somut risk isaretledi')[:200]}",
            layer="technology", chief="ciso", likelihood=3, impact=3,
            mitigation="", source="auto_review",
        ))
        logger.info(f"Executive review otomatik risk kaydi olusturdu: {risk['id']}")

    requires_approval = reviews["cfo"]["cost_flag"]
    audit_task = asyncio.create_task(_audit(
        actor="executive_board", action="review", target=req.workflow,
        decision="requires_approval" if requires_approval else "approved",
        detail=f"cfo_verdict={reviews['cfo'].get('verdict')} ciso_risk_flag={ciso_review.get('risk_flag', False)}",
    ))
    app.state.background_tasks.add(audit_task)
    audit_task.add_done_callback(app.state.background_tasks.discard)

    return {
        "reviews": reviews,
        "requires_user_approval": requires_approval,
        "memory_write_failures": memory_write_failures,
    }


@app.post("/api/v1/risks", dependencies=[Depends(verify_api_key)])
async def create_risk_endpoint(req: RiskCreate):
    return await _create_risk(req)


@app.get("/api/v1/risks", dependencies=[Depends(verify_api_key)])
async def list_risks(layer: Optional[str] = None, status: Optional[str] = None):
    items = await _memory_get_items("global", RISK_REGISTER_SCOPE_KEY, limit=500)
    risks = list(_latest_by_id(items).values())
    if layer:
        risks = [r for r in risks if r.get("layer") == layer]
    if status:
        risks = [r for r in risks if r.get("status") == status]
    risks.sort(key=lambda r: r.get("risk_score", 0), reverse=True)
    return {"risks": risks, "count": len(risks)}


@app.patch("/api/v1/risks/{risk_id}", dependencies=[Depends(verify_api_key)])
async def update_risk(risk_id: str, req: RiskUpdate):
    items = await _memory_get_items("global", RISK_REGISTER_SCOPE_KEY, limit=500)
    current = _latest_by_id(items).get(risk_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Risk bulunamadi")
    updated = dict(current)
    if req.status is not None:
        updated["status"] = req.status
    if req.mitigation is not None:
        updated["mitigation"] = req.mitigation
    updated["updated_at"] = datetime.now(timezone.utc).isoformat()
    ok = await _remember("global", RISK_REGISTER_SCOPE_KEY, updated)
    if not ok:
        raise HTTPException(status_code=502, detail="Risk guncellenemedi")
    return updated


@app.get("/health")
async def health():
    checks = {}
    try:
        resp = await app.state.http.get(f"{settings.AI_GATEWAY_URL}/health", timeout=5.0)
        checks["ai_gateway"] = resp.status_code == 200
    except Exception:
        checks["ai_gateway"] = False
    try:
        resp = await app.state.http.get(f"{settings.MEMORY_API_URL}/health", timeout=5.0)
        checks["memory"] = resp.status_code == 200
    except Exception:
        checks["memory"] = False
    try:
        checks["nats"] = app.state.nc.is_connected
    except Exception:
        checks["nats"] = False
    qc_task = getattr(app.state, "qc_task", None)
    task_alive = qc_task is not None and not qc_task.done()
    heartbeat = getattr(app.state, "heartbeat", {})
    last_loop = heartbeat.get("last_loop")
    heartbeat_ok = last_loop is not None and (datetime.now(timezone.utc) - last_loop).total_seconds() < 60
    checks["chief_qc"] = task_alive and heartbeat_ok
    return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks}
