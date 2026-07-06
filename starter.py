import asyncio

from temporalio.client import Client

from workflow import AgentWorkflow
from worker import TASK_QUEUE

# в последующем переделать под что-то более серьезное 

async def main() -> None:
    """Функция для прогона всего нашего воркфлоу"""
    client = await Client.connect("localhost:7233")

    handle = await client.start_workflow(
        AgentWorkflow.run,
        ["шаг 1: анализ", "шаг 2: генерация", "шаг 3: тесты", "шаг 4: публикация"],
        id="agent-demo-1",
        task_queue=TASK_QUEUE,
    )
    print(f"workflow {handle.id} запущен, ждём результат")

    for line in await handle.result():
        print(" -", line)


if __name__ == "__main__":
    asyncio.run(main())
