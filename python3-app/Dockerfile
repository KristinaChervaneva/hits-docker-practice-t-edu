FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379

COPY requirements.txt .
COPY wheels/ ./wheels/

RUN pip install --no-cache-dir --no-index --find-links=/app/wheels tornado==6.5.3 && \
    pip install --no-cache-dir --no-index --find-links=/app/wheels -r requirements.txt

COPY . .

EXPOSE 8888
CMD ["python", "main.py"]
