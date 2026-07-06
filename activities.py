import asyncio

from temporalio import activity


@activity.defn
async def do_step(step: str) -> str:
    print(f"выполняю шаг: {step}")
    await asyncio.sleep(1.5)
    return f"готово: {step}"
