from temporalio import workflow
from datetime import timedelta


with workflow.unsafe.imports_passed_through():
    from activity import run_cli
    from shared import TaskInput


@workflow.defn
class ExecuteTaskWorkflow:
    """Чуть позже добавить логи(посмотреть в документации)"""

    @workflow.run
    async def run(self, task: TaskInput) -> str:
        return await workflow.execute_activity(
            run_cli,
            task,
            start_to_close_timeout=timedelta(10),
        )
