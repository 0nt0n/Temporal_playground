# Temporal + opencode playground

Демонстрация замены самописного оркестратора задач на Temporal.

API принимает задачу на естественном языке, Temporal прогоняет её через
двухшаговый workflow: AI-агент opencode (LLM через Cloud.ru Evolution
Foundation Models) пишет код, артефакты выгружаются в MinIO, затем второй
агент делает код-ревью и кладёт заметки рядом с артефактами.

```
POST /run {task_id, command}
    -> api (FastAPI) стартует ExecuteTaskWorkflow
    -> Temporal ставит задачу в очередь
    -> worker, шаг 1: agent_cli
         opencode пишет код в workspace -> файлы уезжают в MinIO (tasks/{task_id}/)
    -> worker, шаг 2: agent_cli_review
         скачивает артефакты -> opencode ревьюит -> tasks/{task_id}/review/REVIEW.md
    -> ответ: отчёт агента + список ключей артефактов в MinIO
```

Что даёт Temporal из коробки: ретраи по RetryPolicy, heartbeat (упавший worker
не теряет задачу), дедупликация по workflow id `task-{task_id}`, полная история
выполнения в Web UI. В Temporal хранятся только состояние и метаданные,
большие файлы — в MinIO.

## Структура

```
app/
    config.py          все настройки в одном месте (читаются из env)
    shared.py          TaskInput, TaskRequest, AgentResult, WorkflowResult
    activities.py      agent_cli (генерация + выгрузка), agent_cli_review (ревью),
                       хелперы MinIO: _upload_workspace / _download_workspace
    workflows.py       ExecuteTaskWorkflow — два шага: генерация -> ревью
    worker.py          worker: поллит очередь задач
    api.py             FastAPI: POST /run, GET /health
opencode.json          конфиг opencode (ключ подставляется из env, секретов нет)
docker-compose.yml     локальный MinIO
Dockerfile             общий образ для worker и api
.env.example           шаблон переменных окружения
```

## Переменные окружения

Всё настраивается через env — см. дефолты в `app/config.py`. Менять параметры
можно без пересборки образа: на Railway это Variables + рестарт сервиса.

| Переменная | Назначение | Дефолт |
|---|---|---|
| `TEMPORAL_ADDRESS` | адрес Temporal-сервера | `localhost:7233` |
| `TASK_QUEUE` | имя очереди задач (worker и api — одинаковое!) | `my-task-queue` |
| `CLOUD_RU_API_KEY` | ключ Cloud.ru для opencode | — |
| `MINIO_ENDPOINT` | адрес MinIO S3 API, без `http://` | `localhost:9000` |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | креды MinIO | — |
| `MINIO_BUCKET` | бакет для артефактов (создастся сам) | `artifacts` |
| `MINIO_SECURE` | TLS до MinIO | `false` |
| `ACTIVITY_TIMEOUT_MINUTES` | лимит одного шага | `5` |
| `HEARTBEAT_TIMEOUT_SECONDS` | таймаут heartbeat | `5` |
| `RETRY_MAX_ATTEMPTS` | попыток на activity | `3` |
| `RETRY_INITIAL_INTERVAL_SECONDS` | стартовая пауза ретрая | `1` |

Скопируй `.env.example` в `.env` и заполни ключи. `.env` не коммитится.

## Локальный запуск

```bash
# 0. MinIO (консоль на http://localhost:9001, логин minioadmin/minioadmin)
docker compose up -d

# 1. Temporal-сервер (UI на http://localhost:8233)
temporal server start-dev

# 2. Worker — обязательно с переменными из .env
set -a && source .env && set +a && python -m app.worker

# 3. API (Swagger на http://localhost:8000/docs)
uvicorn app.api:app --port 8000
```

## Как тестить

`command` — это задача для AI-агента обычным текстом, не shell-команда.
Полный прогон (генерация + ревью) занимает несколько минут:

```bash
curl -X POST http://localhost:8000/run -H "Content-Type: application/json" \
  -d '{"task_id":"demo-1","command":"напиши на python функцию fizzbuzz с тестами"}'
```

Что проверить по результату:

- в ответе: `result.message` — отчёт агента, `result.artifacts` — ключи файлов,
  последним должен быть `tasks/demo-1/review/REVIEW.md`;
- в MinIO console (localhost:9001, бакет `artifacts`) — сами файлы и текст ревью;
- в Temporal UI (localhost:8233, workflow `task-demo-1`) — история: два
  activity-шага `agent_cli` и `agent_cli_review`.

Повторный запуск с тем же `task_id` при живом workflow вернёт ошибку — это
дедупликация; после завершения id можно переиспользовать.

### Демо ретраев

Убей MinIO перед запуском — выгрузка артефактов будет падать, Temporal
ретраить (видно в UI), а после `docker start minio` задача сама доедет:

```bash
docker stop minio
curl -X POST http://localhost:8000/run -H "Content-Type: application/json" \
  -d '{"task_id":"retry-demo","command":"напиши hello world на python"}' &
sleep 60 && docker start minio
```

### Демо durable execution

Во время выполнения запроса убей worker (Ctrl+C) и запусти снова —
workflow продолжится с места остановки, curl дождётся результата.

## Docker

```bash
docker build -t tempo-playground .

# worker (команда по умолчанию)
docker run --env-file .env -e TEMPORAL_ADDRESS=host.docker.internal:7233 \
  -e MINIO_ENDPOINT=host.docker.internal:9000 tempo-playground

# api — тот же образ, другая команда
docker run -p 8000:8000 -e TEMPORAL_ADDRESS=host.docker.internal:7233 \
  tempo-playground uvicorn app.api:app --host 0.0.0.0 --port 8000
```

## Деплой на Railway

Пять сервисов:

1. **Temporal** — шаблон Temporal Server из каталога Railway.
2. **bucket** + **console** — шаблон MinIO (bucket — S3 API, console — веб-морда).
3. **worker** — этот репозиторий, команда по умолчанию (`python3 -m app.worker`).
   Variables: `TEMPORAL_ADDRESS` (private-домен Temporal, порт 7233),
   `CLOUD_RU_API_KEY`, `MINIO_ENDPOINT` (private-домен bucket, порт 9000,
   без `http://`), `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY` (креды из сервиса
   bucket), `MINIO_BUCKET`, `MINIO_SECURE=false`.
4. **api** — тот же репозиторий, Custom Start Command:
   `uvicorn app.api:app --host 0.0.0.0 --port $PORT`. Variables: `TEMPORAL_ADDRESS`.

Тест на Railway — тот же curl, но на публичный домен api:

```bash
curl -X POST https://<api-домен>.up.railway.app/run \
  -H "Content-Type: application/json" \
  -d '{"task_id":"railway-1","command":"напиши на python функцию fizzbuzz с тестами"}'
```

Грабли, на которые мы уже наступили (чтобы не наступать снова):

- Railway деплоит из ветки `main` — проверь, что код запушен именно туда;
- `MINIO_ENDPOINT` — это private-домен сервиса **bucket** (см. его
  Settings -> Networking), порт 9000, а не публичный URL и не порт консоли;
- если reference-переменные `${{bucket.MINIO_ROOT_USER}}` не резолвятся
  (в worker приезжает пустота -> `AccessDenied`), вставь значения литералами;
- после смены Variables дождись, пока worker передеплоится, и только потом тести.

## Как opencode получает ключ в контейнере

Локально opencode берёт ключ из `~/.local/share/opencode/auth.json`
(создаётся через `opencode auth login`). В контейнере этого файла нет,
поэтому используется проектный `opencode.json`: провайдер Cloud.ru описан
в конфиге, а ключ подставляется из переменной окружения через
`{env:CLOUD_RU_API_KEY}`. Если провайдер вернёт 401 — проверь, что
переменная задана в окружении процесса worker.
