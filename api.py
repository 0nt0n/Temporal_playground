from fastapi import FastAPI
from temporalio.client import Client

from shared import TaskInput, TaskRequest


app = FastAPI()


@app.post("/run")
async def run_task(req: TaskRequest):
    client = await Client.connect("localhost:7233")

    task = TaskInput(req.task_id, req.command)
    result = await client.execute_workflow(
        "ExecuteTaskWorkflow",
        task,
        id=f"task-{task.task_id}",
        task_queue="my-task-queue",
    )

    return {"task_id": req.task_id, "result": result}