FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl bash && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://opencode.ai/install | bash

ENV PATH="/root/.opencode/bin:$PATH"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY opencode.json .

CMD ["python3", "-m", "app.worker"]
