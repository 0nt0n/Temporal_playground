from temporalio import workflow
from datetime import timedelta
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.activities import agent_cli, agent_cli_review
    from app.shared import TaskInput, WorkflowResult

RETRY_POLICY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=1))


@workflow.defn
class ExecuteTaskWorkflow:

    @workflow.run
    async def run(self, task: TaskInput) -> WorkflowResult:
        result = await workflow.execute_activity(
            agent_cli,
            task,
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(seconds=5),
            retry_policy=RETRY_POLICY,
        )

        review = await workflow.execute_activity(
            agent_cli_review,
            TaskInput(task.task_id, f"Исходная задача была:\n{task.command}"),
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(seconds=5),
            retry_policy=RETRY_POLICY,
        )

        return WorkflowResult(
            message=result.output,
            artifacts=result.artifacts + review.artifacts,
        )
