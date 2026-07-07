import asyncio
from temporalio import activity
from app.shared import TaskInput

# глянуть с lang плагин ...


@activity.defn
async def run_cli(task: TaskInput) -> str:
    proc = await asyncio.create_subprocess_shell(
        task.command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    while True:
        try:
            await asyncio.wait_for(proc.wait(), timeout=2)
            break
        except asyncio.TimeoutError:
            activity.heartbeat("heartbeat details!")
    stdout, stderr = await proc.communicate()

    if proc.returncode == 0:
        return stdout.decode()
    else:
        raise RuntimeError(stderr.decode())
