FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /service
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
USER 10001:10001
CMD ["sh", "-c", "exec uvicorn main:app --app-dir app --host 0.0.0.0 --port ${PORT:-8080}"]
