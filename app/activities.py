import asyncio
import os
from minio import Minio
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


async def _wait_with_heartbeat(awaitable, message: str = "working"):
    """Ждёт awaitable, каждые 2 секунды отправляя heartbeat."""
    task = asyncio.ensure_future(awaitable)
    while True:
        try:
            return await asyncio.wait_for(asyncio.shield(task), timeout=2)
        except asyncio.TimeoutError:
            activity.heartbeat(message)


def connect_to_minio():
    client = Minio(
        os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        secure=os.getenv("MINIO_SECURE", "false") == "true",
    )
    bucket = os.getenv("MINIO_BUCKET", "artifacts")

    return client, bucket


def _upload_workspace(workspace: str, task_id: str) -> list[str]:
    """Загружает все файлы из workspace в MinIO, возвращает ключи объектов"""
    client, bucket = connect_to_minio()

    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    uploaded = []
    for root, _, filenames in os.walk(workspace):
        for name in filenames:
            local_path = os.path.join(root, name)
            relative_path = os.path.relpath(local_path, workspace)
            object_name = f"tasks/{task_id}/{relative_path}"
            client.fput_object(bucket, object_name, local_path)
            uploaded.append(object_name)
    return uploaded


def _download_workspace(task_id: str, workspace: str) -> list[str]:
    """Скачивает все артефакты задачи из MinIO в workspace"""
    client, bucket = connect_to_minio()
    prefix = f"tasks/{task_id}/"

    downloaded = []
    for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
        relative_path = obj.object_name.removeprefix(prefix)
        local_path = os.path.join(workspace, relative_path)
        client.fget_object(bucket, obj.object_name, local_path)
        downloaded.append(local_path)

    if not downloaded:
        raise FileNotFoundError(f"в MinIO нет артефактов задачи {task_id}")
    return downloaded


def _upload_file(local_path: str, object_name: str) -> str:
    """Загружает один файл в MinIO, возвращает ключ объекта."""
    client, bucket = connect_to_minio()

    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    client.fput_object(bucket, object_name, local_path)
    return object_name


@activity.defn
async def agent_cli(task: TaskInput) -> AgentResult:
    workspace = f"/tmp/workspace/{task.task_id}"
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

    artifacts = await _wait_with_heartbeat(
        asyncio.to_thread(_upload_workspace, workspace, task.task_id),
        message="uploading artifacts",
    )

    return AgentResult(answer, artifacts)


@activity.defn
async def agent_cli_review(task: TaskInput) -> AgentResult:
    """Скачивает артефакты задачи, делает ревью кода и грузит заметки в MinIO."""
    workspace = f"/tmp/workspace/{task.task_id}-review"
    os.makedirs(workspace, exist_ok=True)

    await _wait_with_heartbeat(
        asyncio.to_thread(_download_workspace, task.task_id, workspace),
        message="downloading artifacts",
    )

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

    object_name = f"tasks/{task.task_id}/review/REVIEW.md"
    await _wait_with_heartbeat(
        asyncio.to_thread(_upload_file, review_path, object_name),
        message="uploading review",
    )

    return AgentResult(review, [object_name])
