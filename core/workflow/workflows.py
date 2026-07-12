"""
KI Enterprise Workflow Engine - Temporal workflow tanimlari.

Build Order Phase 1'de listelenen 6 workflow: new_project, feature_request,
marketing_campaign, customer_support, research_request, deployment.

Departman/worker katmani (Phase 4/5) henuz kurulmadigi icin her workflow su an:
  1. AI Gateway uzerinden talebi bir plana donusturur (plan_with_ai)
  2. Plani Executive Board'a (CTO/CFO/CMO/COO/CISO, ayri servis - core/executives)
     degerlendirtir (executive_review)
  3. Plani Event Bus'a yayinlar (publish_event, subject: task.<workflow_adi>)
Departmanlar/worker'lar devreye girdikce buraya gercek is dagitim adimlari eklenecek.
"""
import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import executive_review, plan_with_ai, publish_event

# Tek dogruluk kaynagi: workflow adlari. @workflow.defn(name=...) satirlari asagida
# bu listeyle AYNI SIRADA ve AYNI DEGERLERLE elle senkron tutulmali (Temporal decorator'lari
# calisma-zamaninda bu listeden turetilemiyor) - baska dosyalar (main.py, start_workflow.py)
# ise bu listeyi import ederek kullanmali, kendi kopyalarini tutmamali.
WORKFLOW_NAMES = [
    "new_project", "feature_request", "marketing_campaign",
    "customer_support", "research_request", "deployment",
]

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


async def _run(self: ApprovalMixin, workflow_name: str, prompt: str, project: str = "") -> dict:
    # plan_with_ai pahali ve non-deterministik bir LLM cagrisi yapar - korlemesine
    # tekrar hem maliyeti katlar hem de httpx'in kendi 90s timeout'uyla yarisan
    # dar bir activity timeout'una sahipti. Tek deneme + genis timeout.
    # NOT: Daha once "gecici 401" sanip retry=2'ye cikarilmisti - gercek kok neden
    # ayni task queue'da birden fazla stale worker sureci calismasiydi (eski kod
    # calistiran zombie worker'lar). Worker restart disiplini (tek instance,
    # eskisini kesin oldur) ile duzeltildi - retry tekrar 1'e alindi.
    plan = await workflow.execute_activity(
        plan_with_ai,
        args=[workflow_name, prompt],
        start_to_close_timeout=timedelta(seconds=150),
        retry_policy=RetryPolicy(maximum_attempts=1),
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
            return {
                "workflow": workflow_name, "plan": plan["plan"], "event": None, "project": project,
                "executive_review": review["reviews"], "requires_user_approval": True,
                "status": "approval_timeout",
            }

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
    return {
        "workflow": workflow_name, "plan": plan["plan"], "event": ack, "project": project,
        "executive_review": review["reviews"], "requires_user_approval": review["requires_user_approval"],
        "status": "published",
    }


@workflow.defn(name="new_project")
class NewProjectWorkflow(ApprovalMixin):
    @workflow.run
    async def run(self, prompt: str, project: str = "") -> dict:
        return await _run(self, "new_project", prompt, project)


@workflow.defn(name="feature_request")
class FeatureRequestWorkflow(ApprovalMixin):
    @workflow.run
    async def run(self, prompt: str, project: str = "") -> dict:
        return await _run(self, "feature_request", prompt, project)


@workflow.defn(name="marketing_campaign")
class MarketingCampaignWorkflow(ApprovalMixin):
    @workflow.run
    async def run(self, prompt: str, project: str = "") -> dict:
        return await _run(self, "marketing_campaign", prompt, project)


@workflow.defn(name="customer_support")
class CustomerSupportWorkflow(ApprovalMixin):
    @workflow.run
    async def run(self, prompt: str, project: str = "") -> dict:
        return await _run(self, "customer_support", prompt, project)


@workflow.defn(name="research_request")
class ResearchRequestWorkflow(ApprovalMixin):
    @workflow.run
    async def run(self, prompt: str, project: str = "") -> dict:
        return await _run(self, "research_request", prompt, project)


@workflow.defn(name="deployment")
class DeploymentWorkflow(ApprovalMixin):
    @workflow.run
    async def run(self, prompt: str, project: str = "") -> dict:
        return await _run(self, "deployment", prompt, project)


ALL_WORKFLOWS = [
    NewProjectWorkflow,
    FeatureRequestWorkflow,
    MarketingCampaignWorkflow,
    CustomerSupportWorkflow,
    ResearchRequestWorkflow,
    DeploymentWorkflow,
]
