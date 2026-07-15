import asyncio
import os
from temporalio import activity

from app.shared import TaskInput, AgentResult

SYSTEM_PROMPT = (
    "Ты автономный AI-агент для выполнения задач разработки. "
    "Работай непосредственно с файлами в текущей рабочей директории. "
    "Создавай и изменяй файлы, необходимые для выполнения задачи. "
    "Твоя цель — получить рабочий результат, а не предоставить инструкцию. "
    "\n\n"
    "После завершения работы ответ должен содержать:\n"
    "1. Краткое описание выполненной работы.\n"
    "2. Список созданных или измененных файлов.\n"
    "3. Краткий итоговый результат."
)

REVIEW_PROMPT = (
    "Ты опытный код-ревьюер. Изучи код в текущей рабочей директории. "
    "Ничего не изменяй и не создавай — только читай. "
    "\n\n"
    "Ответ должен содержать:\n"
    "1. Общую оценку качества кода и архитектуры.\n"
    "2. Найденные проблемы и потенциальные баги (с путями к файлам).\n"
    "3. Конкретные рекомендации по улучшению."
)


def _workspace_path(task_id: str) -> str:
    return f"/tmp/workspace/{task_id}"


async def _wait_with_heartbeat(awaitable, message: str = "working"):
    """Ждёт awaitable, каждые 2 секунды отправляя heartbeat."""
    task = asyncio.ensure_future(awaitable)
    while True:
        try:
            return await asyncio.wait_for(asyncio.shield(task), timeout=2)
        except asyncio.TimeoutError:
            activity.heartbeat(message)


def _list_workspace(workspace: str) -> list[str]:
    """Возвращает пути всех файлов в workspace."""
    files = []
    for root, _, filenames in os.walk(workspace):
        for name in filenames:
            files.append(os.path.join(root, name))
    return files


@activity.defn
async def agent_cli(task: TaskInput) -> AgentResult:
    workspace = _workspace_path(task.task_id)
    os.makedirs(workspace, exist_ok=True)

    prompt = f"{SYSTEM_PROMPT}\n\nЗадача пользователя:\n{task.command}"

    proc = await asyncio.create_subprocess_exec(
        "opencode",
        "run",
        prompt,
        cwd=workspace,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await _wait_with_heartbeat(proc.communicate())

    if proc.returncode != 0:
        raise RuntimeError(stderr.decode())

    answer = stdout.decode()

    return AgentResult(answer, _list_workspace(workspace))


@activity.defn
async def agent_cli_review(task: TaskInput) -> AgentResult:
    """Делает ревью кода в workspace задачи, заметки кладёт в REVIEW.md."""
    workspace = _workspace_path(task.task_id)
    if not os.path.isdir(workspace) or not _list_workspace(workspace):
        raise FileNotFoundError(f"нет артефактов задачи {task.task_id}")

    prompt = REVIEW_PROMPT
    if task.command:
        prompt += f"\n\nДополнительные указания пользователя:\n{task.command}"

    proc = await asyncio.create_subprocess_exec(
        "opencode",
        "run",
        prompt,
        cwd=workspace,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await _wait_with_heartbeat(proc.communicate(), message="reviewing")

    if proc.returncode != 0:
        raise RuntimeError(stderr.decode())

    review = stdout.decode()

    review_path = os.path.join(workspace, "REVIEW.md")
    with open(review_path, "w") as f:
        f.write(review)

    return AgentResult(review, [review_path])
