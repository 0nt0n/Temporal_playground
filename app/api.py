from fastapi import FastAPI
from temporalio.client import Client

from app import config
from app.shared import TaskInput, TaskRequest


app = FastAPI()


@app.post("/run")
async def run_task(req: TaskRequest):
    client = await Client.connect(config.TEMPORAL_ADDRESS)

    task = TaskInput(req.task_id, req.command)
    result = await client.execute_workflow(
        "ExecuteTaskWorkflow",
        task,
        id=f"task-{task.task_id}",
        task_queue=config.TASK_QUEUE,
    )

    return {"task_id": req.task_id, "result": result}


@app.get('/health')
def check_root():
    return {"message": "healthy"}