from temporalio import workflow
from datetime import timedelta
from temporalio.common import RetryPolicy


with workflow.unsafe.imports_passed_through():
    from app.activities import run_cli
    from app.shared import TaskInput


@workflow.defn
class ExecuteTaskWorkflow:
    """Чуть позже добавить логи(посмотреть в документации)"""

    @workflow.run
    async def run(self, task: TaskInput) -> str:
        return await workflow.execute_activity(
            run_cli,
            task,
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(seconds=5),
            retry_policy=RetryPolicy(
                maximum_attempts=3, initial_interval=timedelta(seconds=1)
            ),
        )
