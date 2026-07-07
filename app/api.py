from fastapi import FastAPI
import os
from temporalio.client import Client

from app.shared import TaskInput, TaskRequest


app = FastAPI()


@app.post("/run")
async def run_task(req: TaskRequest):
    address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    client = await Client.connect(address)

    task = TaskInput(req.task_id, req.command)
    result = await client.execute_workflow(
        "ExecuteTaskWorkflow",
        task,
        id=f"task-{task.task_id}",
        task_queue="my-task-queue",
    )

    return {"task_id": req.task_id, "result": result}
