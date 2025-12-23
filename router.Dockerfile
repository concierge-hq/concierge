FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git curl gcc postgresql-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY src/services/router/requirements.txt ./router_requirements.txt

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r router_requirements.txt
RUN pip install kubernetes openai

COPY src/ ./src/
COPY configs/ ./configs/
COPY scripts/ ./scripts/
COPY setup.py .

RUN pip install -e .

ENV PYTHONPATH=/app/src:/app/concierge
ENV CONCIERGE_CONFIG_PATH=/app/configs/default.yaml

EXPOSE 8080

CMD ["uvicorn", "services.router.main:app", "--host", "0.0.0.0", "--port", "8080"]

