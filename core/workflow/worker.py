import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from config import settings
from activities import executive_review, plan_with_ai, publish_event
from workflows import ALL_WORKFLOWS

logging.basicConfig(level=logging.INFO)


async def main():
    client = await Client.connect(settings.TEMPORAL_HOST, namespace=settings.TEMPORAL_NAMESPACE)
    worker = Worker(
        client,
        task_queue=settings.TASK_QUEUE,
        workflows=ALL_WORKFLOWS,
        activities=[plan_with_ai, executive_review, publish_event],
    )
    print(f"Worker basladi. task_queue={settings.TASK_QUEUE}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
