from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app import config
    from app.activities import agent_cli, agent_cli_review
    from app.shared import TaskInput, WorkflowResult

RETRY_POLICY = RetryPolicy(
    maximum_attempts=config.RETRY_MAX_ATTEMPTS,
    initial_interval=config.RETRY_INITIAL_INTERVAL,
)


@workflow.defn
class ExecuteTaskWorkflow:
    @workflow.run
    async def run(self, task: TaskInput) -> WorkflowResult:
        result = await workflow.execute_activity(
            agent_cli,
            task,
            start_to_close_timeout=config.ACTIVITY_TIMEOUT,
            heartbeat_timeout=config.HEARTBEAT_TIMEOUT,
            retry_policy=RETRY_POLICY,
        )

        review = await workflow.execute_activity(
            agent_cli_review,
            TaskInput(task.task_id, f"Исходная задача была:\n{task.command}"),
            start_to_close_timeout=config.ACTIVITY_TIMEOUT,
            heartbeat_timeout=config.HEARTBEAT_TIMEOUT,
            retry_policy=RETRY_POLICY,
        )

        return WorkflowResult(
            message=result.output,
            artifacts=result.artifacts + review.artifacts,
        )
