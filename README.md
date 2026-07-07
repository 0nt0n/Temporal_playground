# Temporal + opencode playground

Демонстрация замены самописного оркестратора задач на Temporal.
API принимает задачу по HTTP, Temporal ставит её в очередь, worker выполняет
команду (в том числе CLI-агента opencode, который ходит в LLM через
Cloud.ru Evolution Foundation Models) и возвращает результат.

Что даёт Temporal из коробки:

- ретраи упавших задач по RetryPolicy (3 попытки);
- heartbeat: если worker умирает во время выполнения, задача переназначается
  на живой worker;
- дедупликация: workflow id = `task-{task_id}`, два одинаковых task_id
  одновременно запустить нельзя;
- полная история выполнения в Web UI.

## Структура

```
app/
    shared.py          TaskInput (dataclass), TaskRequest (pydantic)
    activities.py      run_cli — запуск команды через subprocess + heartbeat
    workflows.py       ExecuteTaskWorkflow — один activity-вызов с retry
    worker.py          worker: поллит очередь my-task-queue
    api.py             FastAPI: POST /run стартует workflow
opencode.json          конфиг opencode (ключ берётся из env, секретов нет)
Dockerfile             общий образ для worker и api
.env.example           шаблон переменных окружения
```

## Переменные окружения

| Переменная         | Назначение                        | Локальный дефолт  |
|--------------------|-----------------------------------|-------------------|
| `TEMPORAL_ADDRESS` | адрес Temporal-сервера            | `localhost:7233`  |
| `CLOUD_RU_API_KEY` | ключ Cloud.ru для opencode        | из `.env`         |

Скопируй `.env.example` в `.env` и заполни ключ. `.env` не коммитится.

## Локальный запуск

Три терминала:

```bash
# 1. Temporal-сервер (UI на http://localhost:8233)
temporal server start-dev

# 2. Worker
python -m app.worker

# 3. API (Swagger на http://localhost:8000/docs)
uvicorn app.api:app --port 8000
```

Проверка без opencode:

```bash
curl -X POST http://localhost:8000/run -H "Content-Type: application/json" \
  -d '{"task_id":"1","command":"echo hello"}'
```

Запрос с opencode (отвечает минутами — это нормально, таймауты рассчитаны):

```bash
curl -X POST http://localhost:8000/run -H "Content-Type: application/json" \
  -d '{"task_id":"10","command":"opencode run \"напиши hello world на python\""}'
```

## Docker

```bash
docker build -t tempo-playground .

# worker (команда по умолчанию)
docker run --env-file .env -e TEMPORAL_ADDRESS=host.docker.internal:7233 tempo-playground

# api — тот же образ, другая команда
docker run -p 8000:8000 -e TEMPORAL_ADDRESS=host.docker.internal:7233 \
  tempo-playground uvicorn app.api:app --host 0.0.0.0 --port 8000
```

## Деплой на Railway

Три сервиса:

1. **Temporal** — по готовому шаблону Temporal Server из каталога Railway.
2. **worker** — этот репозиторий, команда по умолчанию (`python3 -m app.worker`).
   Variables: `TEMPORAL_ADDRESS` (внутренний адрес сервиса Temporal, порт 7233),
   `CLOUD_RU_API_KEY`.
3. **api** — тот же репозиторий, Custom Start Command:
   `uvicorn app.api:app --host 0.0.0.0 --port $PORT`.
   Variables: `TEMPORAL_ADDRESS`.

## Как opencode получает ключ в контейнере

Локально opencode берёт ключ из `~/.local/share/opencode/auth.json`
(создаётся через `opencode auth login`). В контейнере этого файла нет,
поэтому используется проектный `opencode.json`: провайдер Cloud.ru описан
в конфиге, а ключ подставляется из переменной окружения через
`{env:CLOUD_RU_API_KEY}`. Если провайдер вернёт 401 — проверь, что
переменная задана в окружении процесса worker.
