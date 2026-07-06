from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import do_step


@workflow.defn
class AgentWorkflow:
    @workflow.run
    async def run(self, steps: list[str]) -> list[str]:
        results = []
        for step in steps:
            result = await workflow.execute_activity(
                do_step,
                step,
                start_to_close_timeout=timedelta(seconds=30),
            )
            results.append(result)
        return results
