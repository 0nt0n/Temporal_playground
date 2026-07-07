import asyncio
from temporalio.client import Client
from shared import TaskInput


async def main(task: TaskInput):
    client = await Client.connect("localhost:7233")
    result = await client.execute_workflow(
        "ExecuteTaskWorkflow",
        task,
        id=f"task-{task.task_id}",
        task_queue="my-task-queue",
    )
    print("Workflow result:", result)


if __name__ == "__main__":
    task = TaskInput(task_id="1", command="opencode run 'напиши hello world на python'")
    asyncio.run(main(task))
