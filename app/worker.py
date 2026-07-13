import asyncio
import os
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio import workflow


with workflow.unsafe.imports_passed_through():
    from app.activities import agent_cli, agent_cli_review
    from app.workflows import ExecuteTaskWorkflow


async def main():
    address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    client = await Client.connect(address)
    worker = Worker(
        client,
        task_queue="my-task-queue",
        workflows=[ExecuteTaskWorkflow],
        activities=[agent_cli, agent_cli_review],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
