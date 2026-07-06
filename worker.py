import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio import workflow


with workflow.unsafe.imports_passed_through():
    from activity import run_cli
    from workflow import ExecuteTaskWorkflow


async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="my-task-queue",
        workflows=[ExecuteTaskWorkflow],
        activities=[run_cli],
    )
    print("!!! Воркер запустился !!!")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
