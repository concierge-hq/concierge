# Concierge V0.2
# Dockerfile for Concierge Backend
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl 

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY workers/ ./workers/
COPY configs/ ./configs/
COPY setup.py .

RUN pip install -e .

EXPOSE 8082

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s \
  CMD curl -f http://localhost:8082/health || exit 1

CMD ["python", "-m", "uvicorn", "concierge.serving.api:app", "--host", "0.0.0.0", "--port", "8082"]

