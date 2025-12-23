FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git curl gcc postgresql-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install asyncpg

COPY src/ ./src/
COPY setup.py .

RUN pip install -e .

ENV PYTHONPATH=/app/src:/app

EXPOSE 8080

CMD ["python", "-m", "services.worker.main", "start"]

