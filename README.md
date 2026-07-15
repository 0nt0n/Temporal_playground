# Temporal + opencode playground

Демонстрация замены самописного оркестратора задач на Temporal.

API принимает задачу на естественном языке, Temporal прогоняет её через
двухшаговый workflow: AI-агент opencode (LLM через Cloud.ru Evolution
Foundation Models) пишет код в рабочей директории, затем второй агент
делает код-ревью и кладёт заметки в REVIEW.md рядом с кодом.

```
POST /run {task_id, command}
    -> api (FastAPI) стартует ExecuteTaskWorkflow
    -> Temporal ставит задачу в очередь
    -> worker, шаг 1: agent_cli
         opencode пишет код в /tmp/workspace/{task_id}
    -> worker, шаг 2: agent_cli_review
         opencode ревьюит код -> /tmp/workspace/{task_id}/REVIEW.md
    -> ответ: отчёт агента + список файлов
```

Что даёт Temporal из коробки: ретраи по RetryPolicy, heartbeat (упавший worker
не теряет задачу), дедупликация по workflow id `task-{task_id}`, полная история
выполнения в Web UI.

Артефакты живут в файловой системе worker'а. Ограничение: при нескольких
worker'ах шаг ревью может попасть на другой инстанс и не найти файлы —
для этого случая нужно общее хранилище (S3-совместимое), сейчас вырезано.

## Структура

```
app/
    config.py          все настройки в одном месте (читаются из env)
    shared.py          TaskInput, TaskRequest, AgentResult, WorkflowResult
    activities.py      agent_cli (генерация), agent_cli_review (ревью)
    workflows.py       ExecuteTaskWorkflow — два шага: генерация -> ревью
    worker.py          worker: поллит очередь задач
    api.py             FastAPI: POST /run, GET /health
opencode.json          конфиг opencode (ключ подставляется из env, секретов нет)
Dockerfile             общий образ для worker и api
.env.example           шаблон переменных окружения
```

## Переменные окружения

Всё настраивается через env — дефолты в `app/config.py`. Параметры меняются
без пересборки образа: правишь переменную, рестартуешь сервис.

| Переменная | Назначение | Дефолт |
|---|---|---|
| `TEMPORAL_ADDRESS` | адрес Temporal-сервера | `localhost:7233` |
| `TASK_QUEUE` | имя очереди задач, должно совпадать у worker и api | `my-task-queue` |
| `CLOUD_RU_API_KEY` | ключ Cloud.ru для opencode | — |
| `ACTIVITY_TIMEOUT_MINUTES` | лимит одного шага | `5` |
| `HEARTBEAT_TIMEOUT_SECONDS` | таймаут heartbeat | `5` |
| `RETRY_MAX_ATTEMPTS` | попыток на activity | `3` |
| `RETRY_INITIAL_INTERVAL_SECONDS` | стартовая пауза ретрая | `1` |

Скопируй `.env.example` в `.env` и заполни ключ. `.env` не коммитится.

## Локальный запуск

```bash
# 1. Temporal-сервер (UI на http://localhost:8233)
temporal server start-dev

# 2. Worker (.env подхватывается автоматически)
python -m app.worker

# 3. API (Swagger на http://localhost:8000/docs)
uvicorn app.api:app --port 8000
```

## Как тестить

`command` — задача для AI-агента обычным текстом, не shell-команда.
Полный прогон (генерация + ревью) занимает несколько минут:

```bash
curl -X POST http://localhost:8000/run -H "Content-Type: application/json" \
  -d '{"task_id":"demo-1","command":"напиши на python функцию fizzbuzz с тестами"}'
```

Что проверить по результату:

- в ответе: `result.message` — отчёт агента, `result.artifacts` — пути файлов,
  последним идёт `/tmp/workspace/demo-1/REVIEW.md`;
- сами файлы — в `/tmp/workspace/demo-1/` на машине worker'а;
- в Temporal UI (localhost:8233, workflow `task-demo-1`) — история: два
  activity-шага `agent_cli` и `agent_cli_review`.

Повторный запуск с тем же `task_id` при живом workflow вернёт ошибку — это
дедупликация; после завершения id можно переиспользовать.

### Демо durable execution

Во время выполнения запроса убей worker (Ctrl+C) и запусти снова —
workflow продолжится с места остановки, curl дождётся результата.
История с попытками и ретраями видна в Temporal UI.

## Docker

```bash
docker build -t tempo-playground .

# worker (команда по умолчанию)
docker run --env-file .env -e TEMPORAL_ADDRESS=host.docker.internal:7233 tempo-playground

# api — тот же образ, другая команда
docker run -p 8000:8000 -e TEMPORAL_ADDRESS=host.docker.internal:7233 \
  tempo-playground uvicorn app.api:app --host 0.0.0.0 --port 8000
```

## Деплой

Три сервиса из этого репозитория и Temporal:

1. **Temporal** — свой инстанс (для Railway — шаблон Temporal Server).
2. **worker** — команда по умолчанию (`python3 -m app.worker`).
   Variables: `TEMPORAL_ADDRESS`, `CLOUD_RU_API_KEY`.
3. **api** — тот же образ, команда
   `uvicorn app.api:app --host 0.0.0.0 --port $PORT`.
   Variables: `TEMPORAL_ADDRESS`.

Частые ошибки:

- деплой идёт из ветки `main` — проверь, что код запушен именно туда;
- после смены Variables дождись передеплоя сервиса и только потом тести.

## Как opencode получает ключ в контейнере

Локально opencode берёт ключ из `~/.local/share/opencode/auth.json`
(создаётся через `opencode auth login`). В контейнере этого файла нет,
поэтому используется проектный `opencode.json`: провайдер Cloud.ru описан
в конфиге, а ключ подставляется из переменной окружения через
`{env:CLOUD_RU_API_KEY}`. Если провайдер вернёт 401 — проверь, что
переменная задана в окружении процесса worker.
