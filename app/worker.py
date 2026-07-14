import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio import workflow

from app import config

with workflow.unsafe.imports_passed_through():
    from app.activities import agent_cli, agent_cli_review
    from app.workflows import ExecuteTaskWorkflow


async def main():
    client = await Client.connect(config.TEMPORAL_ADDRESS)
    worker = Worker(
        client,
        task_queue=config.TASK_QUEUE,
        workflows=[ExecuteTaskWorkflow],
        activities=[agent_cli, agent_cli_review],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
