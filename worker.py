import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from activities import do_step
from workflow import AgentWorkflow

TASK_QUEUE = "agent-demo"


async def main() -> None:
    """Воркер,который выполняет мой воркфлоу и ждет задачи"""
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[AgentWorkflow],
        activities=[do_step],
    )
    print("worker запущен")
    await worker.run() # ожидаем завершения работы


if __name__ == "__main__":
    asyncio.run(main())
