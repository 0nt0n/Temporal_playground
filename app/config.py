"""Все настройки приложения в одном месте.

Каждый параметр читается из переменной окружения и имеет дефолт для локальной
разработки. На Railway меняются в Variables сервиса — без пересборки образа.
"""
import os
from datetime import timedelta


TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
TASK_QUEUE = os.getenv("TASK_QUEUE", "my-task-queue")


MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "artifacts")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false") == "true"


ACTIVITY_TIMEOUT = timedelta(minutes=int(os.getenv("ACTIVITY_TIMEOUT_MINUTES", "5")))
HEARTBEAT_TIMEOUT = timedelta(seconds=int(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "5")))
RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
RETRY_INITIAL_INTERVAL = timedelta(
    seconds=int(os.getenv("RETRY_INITIAL_INTERVAL_SECONDS", "1"))
)
