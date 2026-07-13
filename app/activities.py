import asyncio
from temporalio import activity
from app.shared import TaskInput, StepResult


@activity.defn
async def agent_step(task: TaskInput, context: list[str]) -> StepResult:
    system = (
        "Ты автономный агент, решающий задачу пошагово. "
        "Тебе дан контекст предыдущих шагов. Сделай ровно один следующий шаг к решению. "
        "В САМОМ КОНЦЕ ответа обязательно допиши отдельной строкой ровно одно из двух: "
        "'STATUS: done' если задача полностью решена, или 'STATUS: continue' если нужен ещё шаг."
    )
    context_text = "\n".join(context)
    prompt = f"{system}\n\nКонтекст предыдущих шагов:\n{context_text} \n Задача: {task.command}"

    command = f'opencode run "{prompt}"'

    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    while True:
        try:
            await asyncio.wait_for(proc.wait(), timeout=2)
            break
        except asyncio.TimeoutError:
            activity.heartbeat("working")

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(stderr.decode())

    answer = stdout.decode()

    if "STATUS: done" in answer:
        status = "done"
    else:
        status = "continue"

    return StepResult(output=answer, status=status)
