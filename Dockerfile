FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock

COPY app ./app
COPY migrations ./migrations
COPY .env.example ./.env.example

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
