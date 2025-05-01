FROM python:3.11-slim AS builder

WORKDIR /app
COPY reservation-service/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

# copy installed deps
COPY --from=builder /install /usr/local
# copy app code
COPY reservation-service/ ./
# copy shared utils
COPY shared/ ./shared

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app:/app/shared"

RUN adduser --disabled-password --gecos '' appuser
USER appuser

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]
