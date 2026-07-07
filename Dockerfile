# 1. Базовый образ: Python 3.11 в минимальной сборке
FROM python:3.11-slim

# 2. Ставим системные утилиты, нужные для установки opencode
RUN apt-get update && apt-get install -y curl bash && rm -rf /var/lib/apt/lists/*

# 3. Устанавливаем opencode внутрь образа
RUN curl -fsSL https://opencode.ai/install | bash

# 4. Прописываем opencode в PATH, чтобы его было видно
ENV PATH="/root/.opencode/bin:$PATH"

# 5. Рабочая папка внутри контейнера
WORKDIR /app

# 6. Сначала только зависимости (для кэша), потом ставим их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7. Копируем код пакета и конфиг opencode
COPY app/ app/
COPY opencode.json .

# 8. Команда по умолчанию — worker (на Railway для api переопределить на:
#    uvicorn app.api:app --host 0.0.0.0 --port $PORT)
CMD ["python3", "-m", "app.worker"]
