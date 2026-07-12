import hashlib
import json

import httpx
import nats
from temporalio import activity

from config import settings

_nc: nats.NATS | None = None


async def _get_nats() -> nats.NATS:
    """Worker sureci icinde paylasilan tek NATS baglantisi (her cagride yeni
    baglanti acmak yerine)."""
    global _nc
    if _nc is None or not _nc.is_connected:
        _nc = await nats.connect(settings.NATS_URL)
    return _nc


CEO_PERSONA = (
    "Sen John'sun - KI Enterprise'in CEO'susun. Fiziksel bir urun satmiyorsun; "
    "sattigin sey uzmanlik, zaman ve guven - bu yuzden ITIBAR senin gercek urunun, "
    "her karari buna gore tartarsin.\n\n"
    "Soguk kanli ve analitiksin, duygusal tepki vermezsin - her firsati/krizi 'en "
    "kotu senaryo nedir?' ve 'itibar riskimiz ne kadar?' sorularindan gecirirsin. "
    "Hem makro (piyasa, rekabet, teknoloji) hem mikro (tek bir hata, tek bir "
    "sozlesme maddesi) seviyede ayni anda dusunursun. Sirket politikasi 'once "
    "ucretsiz, sonra self-hosted, sonra acik kaynak, sonra ucretli' - harcama "
    "onerirken bu sirayi gozetirsin.\n\n"
    "Seffafligi erdem degil hayatta kalma stratejisi olarak kullanirsin - hatalari "
    "ortbas etmez, vaka calismasina cevirip hesap verebilirligi surece gomersin.\n\n"
    "Kararlarini dayatmazsin, 'satarsin' - departmanlara guvenirsin, mikro-"
    "yonetmezsin; net hedef + net son tarih koyarsin. Ama gerekince statukoyu "
    "bozmaktan cekinmezsin - radikal donusum cesaretin var.\n\n"
    "Sahadan kopmazsin, tempoyu sen belirlersin - hiz senin icin rekabet "
    "avantajidir. (Tek dogruluk kaynagi: core/personas/PERSONAS.md - orada "
    "degisirse burasi da guncellenmeli.)"
)


@activity.defn
async def plan_with_ai(workflow_name: str, prompt: str) -> dict:
    """AI Gateway'in /api/reason ucu uzerinden istegi bir plana donusturur."""
    system_context = (
        f"{CEO_PERSONA}\n\nSana bir '{workflow_name}' is akisi icin bir talep geldi. "
        "Kendi karakterinle, talebi somut ve uygulanabilir adimlara bol."
    )
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.AI_GATEWAY_URL}/api/reason",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json={"prompt": f"{system_context}\n\nTalep: {prompt}"},
            timeout=90.0,
        )
        resp.raise_for_status()
        data = resp.json()
    return {"plan": data["choices"][0]["message"]["content"], "raw": data}


@activity.defn
async def executive_review(workflow_name: str, prompt: str, plan: str) -> dict:
    """Executive Board'a (core/executives, ayri servis) planı degerlendirtir.
    CFO burada 'once ucretsiz, sonra self-hosted, sonra open source, sonra
    ucretli' kuralini uygular - requires_user_approval=true donerse plan
    ucretli bir kaynak icermektedir (henuz engelleyici degil, isaretleyicidir)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.EXECUTIVES_API_URL}/api/v1/executives/review",
            headers={"Authorization": f"Bearer {settings.INTERNAL_API_KEY}"},
            json={"workflow": workflow_name, "prompt": prompt, "plan": plan},
            timeout=90.0,
        )
        resp.raise_for_status()
        return resp.json()


@activity.defn
async def publish_event(subject: str, payload: dict) -> dict:
    """NATS JetStream Event Bus'a yayinlar (bkz. core/events).

    Ayni activity attempt'i (retry) sonucu duplicate event yayinlanmasini
    onlemek icin Nats-Msg-Id header'i, activity'nin deterministik retry
    kimligini tasir - JetStream sunucu tarafinda dedup penceresi (varsayilan
    2dk, bkz. streams.py) icinde ayni id'li mesaji bir kez kabul eder.
    """
    info = activity.info()
    msg_id = hashlib.sha256(
        f"{info.workflow_id}:{info.activity_id}:{subject}".encode()
    ).hexdigest()

    nc = await _get_nats()
    js = nc.jetstream()
    ack = await js.publish(subject, json.dumps(payload).encode(), headers={"Nats-Msg-Id": msg_id})
    return {"stream": ack.stream, "seq": ack.seq}
