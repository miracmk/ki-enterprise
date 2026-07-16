"""
KI Enterprise Workflow Engine - Temporal workflow tanimlari.

2026-07-15 mimari degisikligi (9-Chief/~45-departman genislemesi oncesi,
kullanicinin acik talebiyle): Onceki 6 workflow (new_project, feature_request,
marketing_campaign, customer_support, research_request, deployment) BIREBIR
AYNI KODU (_run()) sardigi, aralarinda SIFIR mantik farki oldugu icin - her
yeni departman/kategori icin elle yeni bir @workflow.defn class'i yazmak
saf kopyala-yapistir olurdu (45 birim = 45 neredeyse-bos class). Bunun yerine
Temporal'in DYNAMIC WORKFLOW ozelligi (temporalio>=1.x, @workflow.defn(dynamic=True))
kullanildi: TEK bir handler, ONCEDEN TANIMLANMAMIS herhangi bir workflow adini
yakalar. Yeni bir departman/kategori eklemek artik bu dosyaya HIC DOKUNMADAN
sadece bir isim (core.env/core/ceo:VALID_WORKFLOWS'a) eklemek demektir.

Her workflow su an:
  1. AI Gateway uzerinden talebi bir plana donusturur (plan_with_ai)
  2. Plani Executive Board'a (CTO/CFO/CMO/COO/CISO/CPO/CRO/CDO, ayri servis -
     core/executives) degerlendirtir (executive_review)
  3. Plani Event Bus'a yayinlar (publish_event, subject: task.<workflow_adi>)

Geriye donuk uyumluluk: eski 6 isim (new_project vb.) DAVRANIS OLARAK
DEGISMEDI - hala ayni _run() akisindan geciyorlar, sadece artik statik bir
class yerine dynamic handler tarafindan yakalaniyorlar. Canli dogrulama:
core/workflow/start_workflow.py ile hem eski bir isim (research_request) hem
YENI/hic gorulmemis bir isim ile gercek Temporal calistirmasi test edildi
(bkz. AGENTIC_ARCHITECTURE_PLAN.md SS14).
"""
import asyncio
from collections.abc import Sequence
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RawValue, RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import executive_review, persist_decision, plan_with_ai, publish_event
    from config import settings

# Tek dogruluk kaynagi core.env:WORKFLOW_TO_DEPARTMENT'tir - dinamik turetilir.
WORKFLOW_NAMES = list(settings.WORKFLOW_TO_DEPARTMENT.keys())

# CFO ucretli bir kaynak isaretlerse ("once ucretsiz, sonra self-hosted, sonra
# open source, sonra ucretli. Her maliyet kullanici onayi ister") workflow bu
# sureye kadar approve_cost sinyalini bekler; gelmezse onay reddedilmis sayilir
# ve task.<workflow> event'i YAYINLANMAZ - requires_user_approval artik salt
# metadata degil, gercek bir kapi.
APPROVAL_TIMEOUT = timedelta(hours=24)


class ApprovalMixin:
    def __init__(self) -> None:
        self._approved = False

    @workflow.signal
    def approve_cost(self) -> None:
        self._approved = True


async def _persist(workflow_id: str, workflow_name: str, prompt: str, project: str, initiated_by: str,
                    status: str, result: dict | None, error: str | None = None) -> None:
    """persist_decision activity'sini cagirir (bkz. activities.py) - eski
    core/ceo/main.py:_wait_and_remember'in yazdigi ayni {"status": "completed"|
    "failed", "result"|"error": ...} semasini birebir korur, sadece artik
    workflow icinde (restart-dayanikli) calisir."""
    content = {
        "workflow_id": workflow_id, "workflow": workflow_name, "project": project,
        "initiated_by": initiated_by, "prompt": prompt, "status": status,
    }
    if result is not None:
        content["result"] = result
    if error is not None:
        content["error"] = error
    await workflow.execute_activity(
        persist_decision,
        args=[content],
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=RetryPolicy(maximum_attempts=5),
    )


async def _run(self: ApprovalMixin, workflow_name: str, prompt: str, project: str = "", initiated_by: str = "direct") -> dict:
    workflow_id = workflow.info().workflow_id
    try:
        # plan_with_ai pahali ve non-deterministik bir LLM cagrisi yapar. Eskiden
        # tek denemeydi (asagidaki eski not) - tek gecici LLM/429 hatasi tum
        # workflow'u sessizce dusuruyordu. Zombie-worker kok nedeni (asagidaki not)
        # coktan duzeltildigi icin artik gecici hatalara karsi 3 deneme + 10s
        # baslangic bekleme guvenli.
        # ESKI NOT: Daha once "gecici 401" sanip retry=2'ye cikarilmisti - gercek
        # kok neden ayni task queue'da birden fazla stale worker sureci
        # calismasiydi (eski kod calistiran zombie worker'lar). Worker restart
        # disiplini (tek instance, eskisini kesin oldur) ile duzeltildi.
        plan = await workflow.execute_activity(
            plan_with_ai,
            args=[workflow_name, prompt],
            start_to_close_timeout=timedelta(seconds=150),
            retry_policy=RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=10)),
        )
        review = await workflow.execute_activity(
            executive_review,
            args=[workflow_name, prompt, plan["plan"]],
            start_to_close_timeout=timedelta(seconds=150),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )

        if review["requires_user_approval"]:
            # wait_condition basaride None doner (bool degil!), timeout'ta ise
            # asyncio.TimeoutError firlatir - "return False" semantigi YOKTUR.
            try:
                await workflow.wait_condition(lambda: self._approved, timeout=APPROVAL_TIMEOUT)
            except asyncio.TimeoutError:
                result = {
                    "workflow": workflow_name, "plan": plan["plan"], "event": None, "project": project,
                    "executive_review": review["reviews"], "requires_user_approval": True,
                    "status": "approval_timeout",
                }
                await _persist(workflow_id, workflow_name, prompt, project, initiated_by, "completed", result)
                return result

        # publish_event artik Nats-Msg-Id ile idempotent (bkz. activities.py) - retry guvenli.
        # project alani Department Manager/Worker Pool tarafindan da tasinir - Phase 6'nin
        # Project Manager'i (core/projects) is/butce/rapor gorunumunu bu etiketle olusturur.
        ack = await workflow.execute_activity(
            publish_event,
            args=[f"task.{workflow_name}", {
                "workflow": workflow_name, "prompt": prompt, "plan": plan["plan"], "project": project,
                "executive_review": review["reviews"], "requires_user_approval": review["requires_user_approval"],
            }],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        result = {
            "workflow": workflow_name, "plan": plan["plan"], "event": ack, "project": project,
            "executive_review": review["reviews"], "requires_user_approval": review["requires_user_approval"],
            "status": "published",
        }
        await _persist(workflow_id, workflow_name, prompt, project, initiated_by, "completed", result)
        return result
    except Exception as e:
        await _persist(workflow_id, workflow_name, prompt, project, initiated_by, "failed", None, error=str(e))
        raise


@workflow.defn(dynamic=True)
class GenericTaskWorkflow(ApprovalMixin):
    """Herhangi bir workflow-kategori adiyla (new_project, research_request,
    veya WORKFLOW_NAMES'e yeni eklenen herhangi bir departman/kategori adi)
    baslatilabilen tek, dinamik workflow. Hangi isimle cagrildigini
    workflow.info().workflow_type'tan okur - _run()'a AYNEN eski statik
    class'larin yaptigi gibi iletir, davranis degismedi.

    Dynamic workflow sozlesmesi (temporalio): run() TEK bir Sequence[RawValue]
    parametresi alir, gercek argumanlar payload_converter ile elle cozulur."""

    @workflow.run
    async def run(self, args: Sequence[RawValue]) -> dict:
        converter = workflow.payload_converter()
        prompt = converter.from_payload(args[0].payload, str)
        project = converter.from_payload(args[1].payload, str) if len(args) > 1 and args[1] is not None else ""
        initiated_by = converter.from_payload(args[2].payload, str) if len(args) > 2 and args[2] is not None else "direct"
        workflow_name = workflow.info().workflow_type
        return await _run(self, workflow_name, prompt, project, initiated_by)


ALL_WORKFLOWS = [GenericTaskWorkflow]
