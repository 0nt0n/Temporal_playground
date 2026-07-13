from temporalio import workflow
from datetime import timedelta
from temporalio.common import RetryPolicy


with workflow.unsafe.imports_passed_through():
    from app.activities import agent_step
    from app.shared import TaskInput


@workflow.defn
class AgentWorkflow:
    @workflow.run
    async def run(self, task: TaskInput) -> list[str]:
        history: list[str] = []
        max_steps = 5

        for i in range(max_steps):
            step = await workflow.execute_activity(
                agent_step,
                args=[task, history],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            history.append(step.output)

            if step.status == "done":
                break

        return history
