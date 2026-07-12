"""Test/CLI amacli: bir workflow calistirir ve sonucu bekler.
Kullanim: ./venv/bin/python start_workflow.py new_project "Landing page projesi baslat"
"""
import argparse
import asyncio
import uuid

from temporalio.client import Client

from config import settings
from workflows import WORKFLOW_NAMES as VALID_WORKFLOW_NAMES


def parse_args():
    parser = argparse.ArgumentParser(description="Bir KI Enterprise workflow'unu calistirir.")
    parser.add_argument("workflow_name", choices=VALID_WORKFLOW_NAMES, help="Calistirilacak workflow adi")
    parser.add_argument("prompt", help="Workflow'a gonderilecek talep metni")
    parser.add_argument("--project", default="", help="Iliskili proje adi (opsiyonel, bkz. Phase 6)")
    return parser.parse_args()


async def main():
    args = parse_args()
    client = await Client.connect(settings.TEMPORAL_HOST, namespace=settings.TEMPORAL_NAMESPACE)
    result = await client.execute_workflow(
        args.workflow_name,
        args=[args.prompt, args.project],
        id=f"{args.workflow_name}-{uuid.uuid4()}",
        task_queue=settings.TASK_QUEUE,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
