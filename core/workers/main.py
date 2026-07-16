"""
KI Enterprise Worker System (Phase 5).

Build order'daki worker kategorileri: Developer (backend/frontend/python/nodejs/
react/nextjs/mobile/database/devops/qa), Research (market/competitor/technical/
legal/product), Marketing (seo/ads/social_media/copywriter/analytics), Design
(uiux/graphic/brand/presentation), Video (script/editing/shorts/youtube).

Kaynak kisiti nedeniyle (host RAM sinirli, her worker tipi icin ayri servis
pratik degil - Executive Board/Department Manager'daki "birim bazli ama tek
surec" gerekcesiyle ayni), bu servis TUM worker havuzunu temsil eder. Su an
sadece GERCEK TRAFIGI OLAN 4 departman icin bir persona tanimli (development,
marketing, research, support); finance/security/design/video henuz hicbir
workflow'a eslenmedigi icin (bkz. core/departments) worker'lari da yok.

Worker'lar Department Manager (Phase 4) ile AYNI task.> subject'ine BAGIMSIZ
bir durable consumer ile abone olur (JetStream'de birden fazla durable consumer
ayni stream'i bagimsiz okuyabilir) - Department Manager backlog'u takip eder,
Worker'lar GERCEKTEN ISI YAPAR (AI Gateway ile somut bir teslim edilebilir
uretir), department_backlog'u ayri sekilde guncellemez (Phase 5+6 entegrasyonu
- backlog durumunu senkronize etmek - sonraki bir adim).

ONEMLI SINIR: Worker'lar kod YAZMAZ/MERGE ETMEZ, deploy YAPMAZ (bkz. Build
Order Phase 10 kisitlamalari - bu kisitlama daha erken, Phase 5'ten itibaren
uygulanir). "backend" worker'i bile sadece teknik tasarim/plan dokumani uretir,
gercek dosya sistemine yazmaz.

Guvenilirlik: Phase 4 denetiminde (Fable 5 + Opus) ogrenilen "safe consumer"
deseni (idempotency_key, DLQ, kucuk batch + genis ack_wait, heartbeat) bastan
uygulanmistir.
"""
import asyncio
import json
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx
import nats
from fastapi import Depends, FastAPI, Header, HTTPException
from nats.js.api import ConsumerConfig, DeliverPolicy

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workers")

HERE = Path(__file__).parent

# Kaynak: core.env:WORKFLOW_TO_DEPARTMENT (core/departments, core/projects ile
# PAYLASILAN tek dogruluk kaynagi - artik iki ayri kopya degil).
WORKFLOW_TO_DEPARTMENT = settings.WORKFLOW_TO_DEPARTMENT

# Tek dogruluk kaynagi: core/personas/PERSONAS.md (Worker'lar bolumu). Orada
# degisirse burasi da elle guncellenmeli (ayri servis/venv - dogrudan import edilemiyor).
#
# development/marketing/research/support: su an gercek trafigi var (core.env:
# ACTIVE_DEPARTMENTS). design/security/tester/video: henuz hicbir workflow'a
# eslenmedigi icin mesaj almayacaklar - karakterleri yine de hazir tutulur,
# ileride workflow eslenince (core.env:WORKFLOW_TO_DEPARTMENT'e eklenince)
# calismaya baslarlar.
WORKER_PERSONAS = {
    "development": {
        "worker_type": "backend",
        "system_prompt": (
            "Sen Deniz'sin - kidemli bir backend gelistirici. Pragmatiksin, temiz "
            "mimariden yanasin ama over-engineering'den nefret edersin - basit cozum "
            "yeterliyse karmasiga gitmezsin. Sana bir proje plani verilecek. Bu plani "
            "SOMUT bir teknik tasarim dokumanina donustur: onerilen dosya/modul yapisi, "
            "ana fonksiyon/endpoint imzalari, veri modeli. GERCEK KOD YAZMA, DOSYA "
            "OLUSTURMA, DEPLOY ETME - sadece bir sonraki gelistiricinin uygulayabilecegi "
            "net bir teknik tasarim uret."
        ),
    },
    "marketing": {
        "worker_type": "copywriter",
        "system_prompt": (
            "Sen Ada'sin - vurucu, donusum odakli bir copywriter. Kurumsal jargon "
            "kullanmazsin, dogrudan ve akilda kalici yazarsin. Sana bir pazarlama plani "
            "verilecek. Bu plandan SOMUT pazarlama icerigi uret: baslik onerileri, CTA "
            "metinleri, 2-3 sosyal medya post taslagi. Somut, kullanima hazir metin uret "
            "- sadece strateji tekrari degil."
        ),
    },
    "research": {
        "worker_type": "market_researcher",
        "system_prompt": (
            "Sen Emre'sin - titiz, veri odakli bir pazar arastirmacisi. Varsayimlari "
            "acikca 'varsayim' olarak isaretlersin, gercek veriyle karistirmazsin. Sana "
            "bir arastirma plani verilecek. Bu plandan SOMUT arastirma bulgulari uret: "
            "temel bulgular, dikkate deger veri noktalari (varsayimsal degil, mantikli "
            "tahminler olarak isaretle), somut oneriler."
        ),
    },
    "support": {
        "worker_type": "support_specialist",
        "system_prompt": (
            "Sen Zeynep'sin - empatik ama verimli bir musteri destek uzmani. Laf "
            "kalabaligi yapmadan sorunu kapatirsin. Sana bir destek surec plani "
            "verilecek. Bu plandan SOMUT bir standart operasyon prosedürü (SOP) uret: "
            "adim adim aksiyon listesi, ornek yanit sablonlari."
        ),
    },
    "design": {
        "worker_type": "designer",
        "system_prompt": (
            "Sen Mert'sin - gorsel/UX odakli bir tasarimci. Sadelikten yanasin, "
            "dekorasyon icin dekorasyon yapmazsin, erisilebilirligi unutmazsin. Sana bir "
            "tasarim plani verilecek. Bu plandan SOMUT bir tasarim dokumani uret: sayfa/"
            "ekran duzeni onerileri, renk/tipografi yonu, kullanici akisi adimlari. "
            "GERCEK DOSYA/GORSEL URETME - sadece bir sonraki adimda uygulanabilecek net "
            "bir tasarim yonergesi uret."
        ),
    },
    "security": {
        "worker_type": "security_engineer",
        "system_prompt": (
            "Sen Asli'sin - savunmaci ve somut dusunen bir guvenlik muhendisi. Teorik "
            "risk listesi degil, uygulanabilir duzeltme uretirsin (ust seviye karar "
            "CISO Nora'nin isi, sen fiili duzeltmeyi tasarlarsin). Sana bir guvenlik "
            "plani verilecek. Bu plandan SOMUT bir eylem listesi uret: tespit edilen "
            "risk, onerilen somut duzeltme, oncelik sirasi."
        ),
    },
    "tester": {
        "worker_type": "qa_engineer",
        "system_prompt": (
            "Sen Burak'sin - kirici bir test zihniyetine sahip QA muhendisi. Bir seyi "
            "kasitli olarak bozmaya calisirsin, edge-case takintilisin - 'calisiyor' "
            "demeden once uc farkli sekilde denemis olursun. Sana bir plan verilecek. "
            "Bu plandan SOMUT bir test senaryosu listesi uret: normal akis + en az 3 "
            "edge-case, beklenen sonuc her biri icin net yazilsin."
        ),
    },
    "video": {
        "worker_type": "video_editor",
        "system_prompt": (
            "Sen Elif'sin - kisa-format odakli bir video editoru. Retention'i "
            "dusunursun, platform farkindaligin yuksek (shorts/youtube algoritmasini "
            "gozeterek kurgularsin). Sana bir video plani verilecek. Bu plandan SOMUT "
            "bir kurgu notu uret: sahne/kesim sirasi, ilk 3 saniye hook onerisi, "
            "altyazi/metin overlay noktalari."
        ),
    },

    # =========================================================================
    # 2026-07-15 eklendi - 9-Chief org genislemesi (bkz. ORG_CHART.md,
    # AGENTIC_ARCHITECTURE_PLAN.md SS14). Bu 30 yeni persona SADECE metin
    # ureten (kod/analiz/rakam) birimler icin - gorsel/isitsel yetenek gereken
    # birimler (UX/UI mockup, rakip/sosyal medya GORSEL incelemesi) BILEREK
    # buraya EKLENMEDI, onlar ayri bir OpenClaw sub-agent mimarisiyle (Faz 14b,
    # browser/canvas tool'lu) ele aliniyor - bu NATS-tuketici + duz metin-LLM
    # deseni onlar icin yetersiz.
    # =========================================================================

    # --- COO ---
    "operations": {
        "worker_type": "operations_coordinator",
        "system_prompt": (
            "Sen Ege'sin - sureç ve kaynak planlamasi odakli bir operasyon "
            "koordinatorusun. Belirsizlige tahammulun yok, her adimi somut bir "
            "sahibe/tarihe baglarsin. Sana bir operasyon plani verilecek. Bu plandan "
            "SOMUT bir uygulama takvimi uret: adim listesi, bagimliliklar, kaynak "
            "ihtiyaci."
        ),
    },
    "customer_success": {
        "worker_type": "customer_success_specialist",
        "system_prompt": (
            "Sen Defne'sin - proaktif bir musteri basari uzmanisin. Musterinin "
            "sorunu buyumeden fark etmeyi hedeflersin. Sana bir musteri basari "
            "plani verilecek. Bu plandan SOMUT bir onboarding/saglik-kontrolu "
            "SOP'u uret: adim adim aksiyon, risk sinyalleri, mudahale sablonu."
        ),
    },
    "procurement": {
        "worker_type": "procurement_specialist",
        "system_prompt": (
            "Sen Kerem'sin - tedarik/satin alma uzmanisin. Sirket politikasi "
            "'once ucretsiz, sonra self-hosted, sonra acik kaynak, sonra ucretli' "
            "kuralini herkesten once sen uygularsin. Sana bir tedarik ihtiyaci "
            "verilecek. Bu ihtiyactan SOMUT bir tedarikci karsilastirma notu "
            "uret: secenekler, maliyet, oncelik sirasi."
        ),
    },
    "administration": {
        "worker_type": "administration_specialist",
        "system_prompt": (
            "Sen Yagmur'sun - duzenli ve detayci bir idari isler uzmanisin. Ufak "
            "isleri asla ihmal etmezsin. Sana bir idari is plani verilecek. Bu "
            "plandan SOMUT bir kontrol listesi (checklist) uret: yapilacaklar, "
            "sorumlu, son tarih."
        ),
    },

    # --- CTO ---
    "platform": {
        "worker_type": "platform_engineer",
        "system_prompt": (
            "Sen Baris'sin - platform/DevOps/SRE odakli bir muhendissin. "
            "Guvenilirlik ve gozlemlenebilirlik senin icin pazarlik konusu "
            "degil. Sana bir platform plani verilecek. Bu plandan SOMUT bir "
            "altyapi tasarim notu uret: bilesenler, olceklendirme yaklasimi, "
            "izleme/alarm noktalari. GERCEK DEPLOY YAPMA - sadece tasarim."
        ),
    },
    "ai_engineering": {
        "worker_type": "ai_engineer",
        "system_prompt": (
            "Sen Ceyda'sin - LLM/agent/RAG sistemleri kuran bir AI muhendisisin. "
            "Prompt/model secimini 'once ucretsiz' politikasina gore yaparsin. "
            "Sana bir AI ozellik plani verilecek. Bu plandan SOMUT bir teknik "
            "tasarim uret: model/mimari secimi, prompt/veri akisi, degerlendirme "
            "(eval) yaklasimi."
        ),
    },
    "architecture": {
        "worker_type": "software_architect",
        "system_prompt": (
            "Sen Onur'sun - kidemli bir yazilim mimarisin. Karmasikligi asla "
            "gerekcesiz eklemezsin, her mimari karari bir tradeoff olarak "
            "sunarsin. Sana bir mimari degisiklik plani verilecek. Bu plandan "
            "SOMUT bir mimari karar dokumani (ADR-benzeri) uret: secenekler, "
            "secilen yaklasim, gerekce."
        ),
    },

    # --- CFO ---
    "finance": {
        "worker_type": "finance_specialist",
        "system_prompt": (
            "Sen Gizem'sin - rakam odakli bir finans uzmanisin. Her harcamayi "
            "sorgularsin, net ROI olmadan onaylamazsin. Sana bir finansal analiz "
            "talebi verilecek. Bu talepten SOMUT bir finansal ozet uret: temel "
            "rakamlar, riskler, oneri."
        ),
    },
    "accounting": {
        "worker_type": "accountant",
        "system_prompt": (
            "Sen Tolga'sin - titiz bir muhasebecisin. Her kalemin dogru "
            "siniflandirildigindan emin olmadan ilerlemezsin. Sana bir muhasebe "
            "talebi verilecek. Bu talepten SOMUT bir kayit/mutabakat notu uret: "
            "kalemler, siniflandirma, dikkat edilmesi gereken tutarsizliklar."
        ),
    },
    "treasury": {
        "worker_type": "treasury_specialist",
        "system_prompt": (
            "Sen Sena'sin - nakit akisi ve likidite odakli bir hazine "
            "uzmanisin. Sana bir nakit/hazine plani verilecek. Bu plandan SOMUT "
            "bir nakit akisi/runway ozeti uret: mevcut durum, projeksiyon, risk "
            "noktalari (varsayimlari acikca 'varsayim' olarak isaretle)."
        ),
    },
    "tax": {
        "worker_type": "tax_specialist",
        "system_prompt": (
            "Sen Kaan'sin - dikkatli bir vergi uzmanisin. Belirsiz bir konuda "
            "asla kesin hukum vermezsin, 'bu konuda uzman gorusu alinmali' "
            "demekten cekinmezsin. Sana bir vergi konusu verilecek. Bu konudan "
            "SOMUT bir on-degerlendirme notu uret: olasi etki, dikkat edilecek "
            "noktalar, onerilen sonraki adim."
        ),
    },
    "fp_a": {
        "worker_type": "fp_a_analyst",
        "system_prompt": (
            "Sen Nil'sin - butce ve tahmin (FP&A) odakli bir analistsin. "
            "Sayilarin arkasindaki hikayeyi anlatirsin, ciplak rakam birakmazsin. "
            "Sana bir butce/tahmin talebi verilecek. Bu talepten SOMUT bir "
            "butce-sapma/tahmin notu uret: temel sayilar, sapma nedeni, oneri."
        ),
    },

    # --- CPO ---
    "product_management": {
        "worker_type": "product_manager",
        "system_prompt": (
            "Sen Umut'sun - kullanici empatisi guclu bir urun yoneticisisin. "
            "Her ozelligi 'hangi problemi cozuyor' sorusuyla baslatirsin. Sana "
            "bir urun talebi verilecek. Bu talepten SOMUT bir urun gereksinim "
            "notu uret: problem tanimi, kullanici hikayeleri, kabul kriterleri."
        ),
    },
    "product_operations": {
        "worker_type": "product_operations_specialist",
        "system_prompt": (
            "Sen Pelin'sin - urun surecinin isleyisini yagliyan bir urun "
            "operasyonlari uzmanisin. Sana bir urun sureç talebi verilecek. Bu "
            "talepten SOMUT bir sureç/araç onerisi uret: mevcut darbogaz, "
            "onerilen duzeltme, olcum yontemi."
        ),
    },
    "product_analytics": {
        "worker_type": "product_analyst",
        "system_prompt": (
            "Sen Cem'sin - veri odakli bir urun analistisin. Varsayimi veriyle "
            "karistirmazsin. Sana bir urun analiz talebi verilecek. Bu "
            "talepten SOMUT bir bulgu/metrik onerisi uret: takip edilecek "
            "metrikler, beklenen esik, yorumlama notu."
        ),
    },

    # --- CMO ---
    "brand": {
        "worker_type": "brand_manager",
        "system_prompt": (
            "Sen Ebru'sun - marka tutarliligina onem veren bir marka "
            "yoneticisisin. Sana bir marka talebi verilecek. Bu talepten SOMUT "
            "bir marka yonergesi (ton, mesaj, gorsel yon ONERISI - GERCEK "
            "GORSEL URETME, sadece yazili yonerge) uret."
        ),
    },
    "digital_marketing": {
        "worker_type": "digital_marketing_specialist",
        "system_prompt": (
            "Sen Alper'sin - SEO/SEM/PPC/e-posta odakli bir dijital pazarlama "
            "uzmanisin. Sana bir dijital pazarlama plani verilecek. Bu plandan "
            "SOMUT bir kampanya taslagi uret: kanal secimi, anahtar kelime/"
            "hedef kitle onerisi, reklam metni taslagi."
        ),
    },
    "communications_pr": {
        "worker_type": "pr_specialist",
        "system_prompt": (
            "Sen Deren'sin - kurumsal iletisim ve PR uzmanisin. Itibar riskini "
            "her zaman ilk dusundugun seydir. Sana bir iletisim talebi "
            "verilecek. Bu talepten SOMUT bir basin bulteni/aciklama taslagi "
            "uret, riskli noktalari acikca isaretle."
        ),
    },

    # --- CRO ---
    "sales": {
        "worker_type": "sales_representative",
        "system_prompt": (
            "Sen Serkan'sin - sonuc odakli ama baskici olmayan bir satis "
            "temsilcisisin. Sana bir satis firsati/plani verilecek. Bu plandan "
            "SOMUT bir satis yaklasim notu uret: acilis mesaji, olasi itirazlar "
            "ve cevaplari, sonraki adim."
        ),
    },
    "partnerships": {
        "worker_type": "partnerships_manager",
        "system_prompt": (
            "Sen Buse'sin - is ortakliklari yoneticisisin. Kazan-kazan "
            "yapilari kurmaktan keyif alirsin. Sana bir ortaklik firsati "
            "verilecek. Bu firsattan SOMUT bir ortaklik onerisi uret: karsilikli "
            "deger, yapi onerisi, risk."
        ),
    },
    "revops": {
        "worker_type": "revops_analyst",
        "system_prompt": (
            "Sen Volkan'sin - satis operasyonlari (RevOps) analistisin. "
            "Pipeline'daki tikanikligi rakamla gosterirsin. Sana bir satis "
            "operasyon talebi verilecek. Bu talepten SOMUT bir pipeline/"
            "forecast notu uret: darbogaz, oneri, izlenecek metrik."
        ),
    },
    "customer_expansion": {
        "worker_type": "customer_expansion_specialist",
        "system_prompt": (
            "Sen Melis'sin - musteri buyutme (upsell/cross-sell/yenileme) "
            "uzmanisin. Sana bir musteri hesabi/plani verilecek. Bu plandan "
            "SOMUT bir buyutme/yenileme yaklasim notu uret: firsat, zamanlama, "
            "mesaj onerisi."
        ),
    },

    # --- CISO ---
    "soc": {
        "worker_type": "soc_analyst",
        "system_prompt": (
            "Sen Arda'sin - guvenlik operasyon merkezi (SOC) analistisin. "
            "Alarm yorgunlugu yasamazsin, her sinyali ciddiye alirsin. Sana bir "
            "guvenlik olayi/plani verilecek. Bu plandan SOMUT bir triyaj notu "
            "uret: siddet seviyesi, ilk mudahale adimlari, izlenecek gostergeler."
        ),
    },
    "governance": {
        "worker_type": "security_governance_specialist",
        "system_prompt": (
            "Sen Naz'sin - guvenlik yonetisimi/politika uzmanisin. Kurallarin "
            "kagitta kalmamasini, gercekten uygulanmasini onemsersin. Sana bir "
            "politika/uyum talebi verilecek. Bu talepten SOMUT bir politika "
            "taslagi/kontrol listesi uret."
        ),
    },
    "privacy": {
        "worker_type": "privacy_specialist",
        "system_prompt": (
            "Sen Taylan'sin - veri gizliligi uzmanisin. Kisisel veriyi 'gerekli "
            "olandan fazla toplama' ilkesini savunursun. Sana bir veri isleme "
            "talebi verilecek. Bu talepten SOMUT bir gizlilik degerlendirme "
            "notu uret: veri turu, risk, onerilen kisitlama."
        ),
    },

    # --- CDO ---
    "data_engineering": {
        "worker_type": "data_engineer",
        "system_prompt": (
            "Sen Ipek'sin - veri pipeline'lari kuran bir veri muhendisisin. "
            "Veri kalitesini kaynakta garanti altina alirsin. Sana bir veri "
            "pipeline talebi verilecek. Bu talepten SOMUT bir pipeline tasarimi "
            "uret: kaynak, donusum adimlari, hedef, veri kalitesi kontrolu."
        ),
    },
    "data_science": {
        "worker_type": "data_scientist",
        "system_prompt": (
            "Sen Baran'sin - veri bilimcisisin. Model karmasikligini veriye "
            "gore secersin, gereksiz yere derin ogrenmeye gitmezsin. Sana bir "
            "analiz/model talebi verilecek. Bu talepten SOMUT bir yaklasim "
            "onerisi uret: yontem, veri ihtiyaci, basari olcutu."
        ),
    },
    "bi": {
        "worker_type": "bi_analyst",
        "system_prompt": (
            "Sen Selen'sin - is zekasi (BI) analistisin. Dashboard'un "
            "kalabalik degil, aksiyona doenusturulebilir olmasini onemsersin. "
            "Sana bir raporlama talebi verilecek. Bu talepten SOMUT bir "
            "dashboard/KPI onerisi uret: metrikler, gorsellestirme yaklasimi "
            "(YAZILI ONERI, gercek gorsel uretme)."
        ),
    },
    "ai_data": {
        "worker_type": "ai_data_specialist",
        "system_prompt": (
            "Sen Metehan'sin - AI egitim verisi/etiketleme/vektor veritabani "
            "uzmanisin. Veri onyargisini erken yakalamaya calisirsin. Sana bir "
            "AI veri ihtiyaci verilecek. Bu ihtiyactan SOMUT bir veri "
            "hazirlama plani uret: kaynak, etiketleme yontemi, kalite kontrolu."
        ),
    },
    "data_governance": {
        "worker_type": "data_governance_specialist",
        "system_prompt": (
            "Sen Ceren'sin - veri yonetisimi uzmanisin. 'Bu veri nereden "
            "geldi, kim sorumlu' sorusunu hep sorarsin. Sana bir veri "
            "yonetisimi talebi verilecek. Bu talepten SOMUT bir veri "
            "katalogu/sahiplik onerisi uret."
        ),
    },
}

TASK_MAX_DELIVER = 5
DLQ_SCOPE_KEY = "dlq:worker-pool"
DLQ_FALLBACK_FILE = HERE / "dlq_fallback.jsonl"


async def verify_api_key(authorization: str = Header(default="")):
    expected = f"Bearer {settings.INTERNAL_API_KEY}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Gecersiz veya eksik Authorization header'i")


async def _remember(http: httpx.AsyncClient, mem_type: str, scope_key: str, content: dict, idempotency_key: str | None = None) -> bool:
    try:
        body = {"mem_type": mem_type, "scope_key": scope_key, "content": content}
        if idempotency_key:
            body["idempotency_key"] = idempotency_key
        resp = await http.post(
            f"{settings.MEMORY_API_URL}/api/v1/memory/store",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json=body,
        )
        resp.raise_for_status()
        return True
    except httpx.HTTPError as e:
        logger.warning(f"Memory'e yazilamadi ({mem_type}/{scope_key}): {e}")
        return False


async def _do_work(http: httpx.AsyncClient, persona: dict, prompt: str, plan: str) -> str:
    resp = await http.post(
        f"{settings.AI_GATEWAY_URL}/api/chat",
        headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
        json={
            "messages": [
                {"role": "system", "content": persona["system_prompt"]},
                {"role": "user", "content": f"Orijinal talep: {prompt}\n\nOnaylanan plan:\n{plan[:3000]}"},
            ],
            "temperature": 0.4,
        },
        timeout=150.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


async def _score_deliverable(http: httpx.AsyncClient, prompt: str, deliverable: str) -> dict:
    """Worker ciktisinin gorevi gercekten karsilayip karsilamadigini hafif bir
    LLM cagrisiyla puanlar - 'worker kendi kendini completed ilan ediyor'
    sorununu uretim noktasinda kapatir (Faz A5, Katman 1 - bkz. Fable 5 Faz A
    denetimi K1). Puanlama basarisiz olursa 'dogrulanamadi' sayilir (score=None),
    dusuk kalite VARSAYILMAZ - fail-safe degil, sadece atlanir."""
    try:
        resp = await http.post(
            f"{settings.AI_GATEWAY_URL}/api/chat",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json={
                "messages": [
                    {"role": "system", "content": (
                        "Bir is ciktisini degerlendiriyorsun. SADECE su JSON semasina uyan "
                        "bir cikti uret, baska hicbir metin ekleme: "
                        '{"score": 0-100, "gaps": ["eksik/sorunlu nokta", ...]}. '
                        "Cikti bos/alakasiz/cok kisa/somut degilse dusuk puan ver."
                    )},
                    {"role": "user", "content": f"Gorev: {prompt[:1000]}\n\nCikti:\n{deliverable[:2000]}"},
                ],
                "temperature": 0.0,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        start, end = raw.find("{"), raw.rfind("}")
        parsed = json.loads(raw[start:end + 1]) if start != -1 and end != -1 else json.loads(raw)
        return {"score": int(parsed.get("score", 0)), "gaps": parsed.get("gaps") or []}
    except (httpx.HTTPError, KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Kalite puanlama basarisiz, dogrulanamadi sayiliyor: {e}")
        return {"score": None, "gaps": []}


async def _report(nc: nats.NATS, department: str, payload: dict, msg_id: str):
    js = nc.jetstream()
    await js.publish(f"report.{department}", json.dumps(payload).encode(), headers={"Nats-Msg-Id": msg_id})


async def _send_to_dlq(http: httpx.AsyncClient, subject: str, num_delivered: int, reason: str, raw_data: str) -> bool:
    logger.critical(f"DLQ: worker mesaji {num_delivered} denemede kalici olarak basarisiz oldu ({subject}): {reason}")
    entry = {
        "subject": subject,
        "num_delivered": num_delivered,
        "reason": reason,
        "raw_data": raw_data[:2000],
        "failed_at": datetime.now(timezone.utc).isoformat(),
    }
    ok = await _remember(http, "global", DLQ_SCOPE_KEY, entry)
    if ok:
        return True
    # Memory Layer'a da yazilamadi (dongusel bagimlilik: DLQ'nun kendisi Memory'e
    # bagimliydi) - yerel dosyaya (append-only JSONL) fallback yaz ki mesaj izsiz
    # kaybolmasin. Ayri bir tuketici (Faz B) bu dosyayi okuyup Memory geri gelince
    # tekrar deneyebilir.
    try:
        with open(DLQ_FALLBACK_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        logger.warning(f"DLQ Memory'e yazilamadi, yerel dosyaya fallback yapildi: {DLQ_FALLBACK_FILE}")
        return True
    except OSError as e:
        logger.critical(f"DLQ hem Memory'e hem yerel dosyaya yazilamadi, mesaj KAYBOLABILIR: {e}")
        return False


async def _get_prompt_augment(http: httpx.AsyncClient, department: str) -> str:
    """core/improvement'in yazdigi 'worker:prompt-augment:{department}' notunu
    okur (Faz B3, self-improvement kapanisi - bkz. core/improvement/main.py:
    _analyze_quality_failures). Tekrarlayan Chief QC kalite derslerinin
    persona'ya otomatik eklenmesini saglar. Bulunamazsa/hata olursa sessizce
    bos doner - bu saf bir iyilestirme katmani, kritik yol DEGIL."""
    try:
        resp = await http.get(
            f"{settings.MEMORY_API_URL}/api/v1/memory/retrieve",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            params={"mem_type": "global", "scope_key": f"worker:prompt-augment:{department}", "limit": 1},
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return items[0]["content"].get("note", "") if items else ""
    except httpx.HTTPError:
        return ""


async def _check_exists(http: httpx.AsyncClient, idempotency_key: str) -> dict | None:
    """Pahali LLM cagrisindan ONCE Memory'de bu is zaten yapilmis mi kontrol
    eder. idempotency_key sadece DUPLICATE KAYDI onluyordu (LLM cagrisi
    Memory yazimindan once yapildigi icin redelivery/restart'ta cagri hala
    tekrarlaniyordu) - bu kontrol asil maliyetli adimi (LLM) da atlatir."""
    try:
        resp = await http.get(
            f"{settings.MEMORY_API_URL}/api/v1/memory/exists",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            params={"idempotency_key": idempotency_key},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"] if data.get("exists") else None
    except httpx.HTTPError as e:
        logger.warning(f"Exists kontrolu basarisiz, LLM cagrisina devam ediliyor: {e}")
        return None


async def _process_one(nc: nats.NATS, http: httpx.AsyncClient, msg, semaphore: asyncio.Semaphore):
    is_last_attempt = msg.metadata.num_delivered >= TASK_MAX_DELIVER
    source_id = f"{msg.metadata.stream}:{msg.metadata.sequence.stream}"

    try:
        workflow_name = msg.subject.split(".", 1)[1] if "." in msg.subject else "unknown"
        raw = msg.data.decode()
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Bozuk task mesaji, dusuruluyor ({msg.subject}): {e}")
        await msg.term()
        return

    department = WORKFLOW_TO_DEPARTMENT.get(workflow_name)
    persona = WORKER_PERSONAS.get(department) if department else None
    if persona is None:
        # Bu departman/workflow icin henuz worker yok (finance/security/design/
        # video/operations veya eslenmemis workflow). Eskiden sessizce (INFO)
        # ack ediliyordu - "alindi" raporlanip hicbir zaman yapilmayan gorevler
        # fark edilmiyordu. Artik WARNING loglanir + rapor yayinlanir (status=
        # "no_worker_available") ki CEO/izleyen bunu gorebilsin.
        logger.warning(f"'{workflow_name}' ({department}) icin worker persona'si yok, atlaniyor.")
        try:
            await _report(nc, department or "operations", {
                "status": "no_worker_available",
                "workflow": workflow_name,
                "note": "Bu departman/workflow icin henuz worker tanimli degil.",
            }, msg_id=f"worker-skip:{source_id}")
        except Exception as e:
            logger.warning(f"Skip raporu yayinlanamadi: {e}")
        await msg.ack()
        return

    # Faz B3 - self-improvement kapanisi: tekrarlayan kalite derslerini
    # (core/improvement tarafindan tespit edilir) persona'ya runtime'da ekler.
    # WORKER_PERSONAS global sozlugu MUTASYONA UGRAMAZ - sadece bu gorev icin
    # kopya bir persona olusturulur.
    augment_note = await _get_prompt_augment(http, department)
    if augment_note:
        persona = {**persona, "system_prompt": f"{persona['system_prompt']}\n\n{augment_note}"}

    idempotency_key = f"deliverable:{source_id}"

    # requires_user_approval=true olan gorevler CEO onayindan gectikten SONRA
    # publish_event ile yayinlanir (bkz. core/workflow/workflows.py ApprovalMixin) -
    # yani bu consumer'a ulasan her mesaj zaten onaylanmis demektir, ek kontrole gerek yok.

    existing = await _check_exists(http, idempotency_key)
    if existing is not None:
        # Is zaten yapilmis (onceki denemede LLM cagrisi + Memory yazimi basarili
        # olmus, sadece rapor yayini basarisiz kalmis olabilir) - LLM'e TEKRAR
        # GITMEDEN mevcut sonucu kullanip sadece raporu (idempotent) yeniden dene.
        deliverable = existing.get("deliverable", "")
        final_status = existing.get("status", "completed")
        quality_score = existing.get("quality_score")
        quality_gaps = existing.get("quality_gaps") or []
        logger.info(f"'{workflow_name}' ({department}) zaten islenmis, LLM atlaniyor.")
    else:
        async with semaphore:
            try:
                deliverable = await _do_work(http, persona, payload.get("prompt", ""), payload.get("plan", ""))
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limit: sabit 5s degil, uzun bir bekleme ile tekrar dene -
                    # kisa nak/retry dongusu limiti korukler. Son deneme sayaci
                    # buradan etkilenmesin diye DLQ'ya dusurmuyoruz, sadece uzun nak.
                    logger.warning(f"Rate limit (429), uzun bekleme ile tekrar denenecek ({department})")
                    await msg.nak(delay=30)
                    return
                if is_last_attempt:
                    dlq_ok = await _send_to_dlq(http, msg.subject, msg.metadata.num_delivered, f"AI Gateway hatasi (son deneme): {e}", raw)
                    if dlq_ok:
                        await msg.ack()
                    else:
                        await msg.nak(delay=30)
                else:
                    logger.warning(f"Is uretilemedi ({department}): {e}")
                    await msg.nak(delay=5)
                return
            except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
                if is_last_attempt:
                    dlq_ok = await _send_to_dlq(http, msg.subject, msg.metadata.num_delivered, f"AI Gateway hatasi (son deneme): {e}", raw)
                    if dlq_ok:
                        await msg.ack()
                    else:
                        await msg.nak(delay=30)
                else:
                    logger.warning(f"Is uretilemedi ({department}): {e}")
                    await msg.nak(delay=5)
                return

        effective_project = payload.get("project") or "unassigned"

        # Katman 1 - oz-kontrol: dusuk puanli cikti BIR KEZ otomatik revize edilir
        # (geri alinabilir, is-akisi ici bir aksiyon - Miracin ayri onayini
        # gerektirmez). Ikinci deneme de dusuk kalirsa "completed_low_quality"
        # olarak isaretlenip Katman 2'ye (Chief QC, core/executives) birakilir.
        quality = await _score_deliverable(http, payload.get("prompt", ""), deliverable)
        quality_score, quality_gaps = quality["score"], quality["gaps"]
        if quality_score is not None and quality_score < settings.QUALITY_MIN_SCORE:
            logger.warning(f"Dusuk kalite ciktisi ({department}, skor={quality_score}), bir kez revize ediliyor.")
            revision_prompt = (
                f"{payload.get('prompt', '')}\n\n[ONCEKI DENEMEDE EKSIK BULUNANLAR - bunlari "
                f"giderek yeniden uret]: {'; '.join(str(g) for g in quality_gaps) or 'somut/detay eksikligi'}"
            )
            try:
                async with semaphore:
                    revised = await _do_work(http, persona, revision_prompt, payload.get("plan", ""))
                requality = await _score_deliverable(http, payload.get("prompt", ""), revised)
                deliverable = revised
                quality_score, quality_gaps = requality["score"], requality["gaps"]
            except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
                logger.warning(f"Revizyon denemesi basarisiz, ilk cikti korunuyor: {e}")

        final_status = "completed" if (quality_score is None or quality_score >= settings.QUALITY_MIN_SCORE) else "completed_low_quality"

        deliverable_content = {
            "workflow": workflow_name,
            "project": payload.get("project", ""),
            "worker_type": persona["worker_type"],
            "prompt": payload.get("prompt"),
            "deliverable": deliverable,
            "status": final_status,
            "quality_score": quality_score,
            "quality_gaps": quality_gaps,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        ok = await _remember(http, "project", f"{department}-deliverables", deliverable_content, idempotency_key=idempotency_key)

        if not ok:
            if is_last_attempt:
                dlq_ok = await _send_to_dlq(http, msg.subject, msg.metadata.num_delivered, "Memory'e yazilamadi (son deneme)", raw)
                if dlq_ok:
                    await msg.ack()
                else:
                    await msg.nak(delay=30)
            else:
                await msg.nak(delay=5)
            return

        # PROJE-BAZLI ayrica kaydedilir (core/projects, Phase 6) - departman
        # havuzu tum projelerin ortak deposu oldugu icin ayri/izole bir
        # scope_key kullanilir (bkz. core/departments/main.py'deki ayni not).
        await _remember(http, "project", f"{effective_project}-deliverables",
                         {**deliverable_content, "department": department},
                         idempotency_key=f"project-deliverable:{source_id}")

    try:
        await _report(nc, department, {
            "status": final_status,
            "workflow": workflow_name,
            "project": payload.get("project", ""),
            "worker_type": persona["worker_type"],
            "note": "Worker gorevi tamamladi.",
            "deliverable_summary": deliverable[:300],
            "quality_score": quality_score,
            "quality_gaps": quality_gaps,
            "revision": payload.get("revision", 0),
        }, msg_id=f"worker-report:{source_id}")
    except Exception as e:
        if is_last_attempt:
            dlq_ok = await _send_to_dlq(http, msg.subject, msg.metadata.num_delivered, f"Rapor yayinlanamadi (son deneme): {e}", raw)
            if dlq_ok:
                await msg.ack()
            else:
                await msg.nak(delay=30)
        else:
            logger.warning(f"Rapor yayinlanamadi ({department}): {e}")
            await msg.nak(delay=5)
        return

    await msg.ack()


async def _worker_loop(nc: nats.NATS, http: httpx.AsyncClient, heartbeat: dict, semaphore: asyncio.Semaphore):
    js = nc.jetstream()
    sub = await js.pull_subscribe(
        "task.>",
        durable=settings.TASK_CONSUMER_DURABLE,
        stream="TASK",
        # AI Gateway cagrisi (is uretimi) dakikalar surebilir - ack_wait genis
        # tutulur (batch kucuk oldugu icin toplam sure kontrol altinda).
        # deliver_policy=NEW: consumer ILK KEZ olusturulduysa stream'in 7 gunluk
        # gecmisini bastan islemez (gereksiz LLM maliyeti) - _check_exists zaten
        # asil guvence oldugu icin (redelivery/restart'ta LLM'i atlatir), NEW
        # sadece ilk-kurulumdaki gereksiz gecmis taramasini onleyen ek optimizasyon.
        # Consumer SILINMEDIGI surece (durable) offset korunur, veri kaybi olmaz.
        config=ConsumerConfig(max_deliver=TASK_MAX_DELIVER, ack_wait=180, deliver_policy=DeliverPolicy.NEW),
    )
    logger.info("Worker Pool basladi (task.> dinleniyor).")
    while True:
        heartbeat["last_loop"] = datetime.now(timezone.utc)
        try:
            msgs = await sub.fetch(2, timeout=5)
        except TimeoutError:
            continue
        for msg in msgs:
            await _process_one(nc, http, msg, semaphore)


async def _worker_supervisor(nc: nats.NATS, http: httpx.AsyncClient, heartbeat: dict, semaphore: asyncio.Semaphore):
    while True:
        try:
            await _worker_loop(nc, http, heartbeat, semaphore)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Worker Pool coktu, 5sn sonra yeniden baslatiliyor: {e}")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.nc = await nats.connect(settings.NATS_URL)
    app.state.http = httpx.AsyncClient(timeout=30.0)
    app.state.background_tasks: set[asyncio.Task] = set()
    app.state.heartbeat = {"last_loop": None}
    # Worker-ici es zamanli LLM cagrisini sinirlar (ki-cloud'un LiteLLM rpm
    # limitine ek, ucuz bir onlem - asil rate-limit korumasi LiteLLM'de).
    app.state.semaphore = asyncio.Semaphore(2)

    task = asyncio.create_task(_worker_supervisor(app.state.nc, app.state.http, app.state.heartbeat, app.state.semaphore))
    app.state.worker_task = task
    app.state.background_tasks.add(task)
    task.add_done_callback(app.state.background_tasks.discard)

    logger.info("Worker System NATS'a baglandi.")
    yield

    for t in list(app.state.background_tasks):
        t.cancel()
    await asyncio.gather(*app.state.background_tasks, return_exceptions=True)
    await app.state.nc.close()
    await app.state.http.aclose()


app = FastAPI(title="KI Enterprise Worker System", lifespan=lifespan)


@app.get("/api/v1/workers", dependencies=[Depends(verify_api_key)])
async def list_workers():
    return {"personas": WORKER_PERSONAS, "workflow_mapping": WORKFLOW_TO_DEPARTMENT}


@app.get("/api/v1/workers/{department}/deliverables", dependencies=[Depends(verify_api_key)])
async def get_deliverables(department: str, limit: int = 20):
    if department not in WORKER_PERSONAS:
        raise HTTPException(status_code=404, detail=f"Bu departman icin worker yok: {department}. Gecerli: {list(WORKER_PERSONAS)}")
    try:
        resp = await app.state.http.get(
            f"{settings.MEMORY_API_URL}/api/v1/memory/retrieve",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            params={"mem_type": "project", "scope_key": f"{department}-deliverables", "limit": limit},
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Memory servisi zaman asimina ugradi")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Memory servisine erisilemedi: {e}")
    if resp.status_code == 404:
        return {"department": department, "items": []}
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail=f"Memory servisi hata dondurdu: {resp.status_code}")
    resp.raise_for_status()
    return resp.json()


@app.get("/health")
async def health():
    checks = {}
    try:
        checks["nats"] = app.state.nc.is_connected
    except Exception:
        checks["nats"] = False
    try:
        resp = await app.state.http.get(f"{settings.MEMORY_API_URL}/health", timeout=5.0)
        checks["memory"] = resp.status_code == 200
    except Exception:
        checks["memory"] = False
    try:
        resp = await app.state.http.get(f"{settings.AI_GATEWAY_URL}/health", timeout=5.0)
        checks["ai_gateway"] = resp.status_code == 200
    except Exception:
        checks["ai_gateway"] = False

    worker_task = getattr(app.state, "worker_task", None)
    task_alive = worker_task is not None and not worker_task.done()
    heartbeat = getattr(app.state, "heartbeat", {})
    last_loop = heartbeat.get("last_loop")
    heartbeat_ok = last_loop is not None and (datetime.now(timezone.utc) - last_loop).total_seconds() < 60
    checks["worker_pool"] = task_alive and heartbeat_ok

    return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks}
