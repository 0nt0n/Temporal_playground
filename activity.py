from temporalio import activity
from shared import TaskInput


@activity.defn
async def run_cli(task: TaskInput) -> str:
    return f"id: {task.task_id},command: {task.command}"
