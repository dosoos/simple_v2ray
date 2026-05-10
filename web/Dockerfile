FROM python:3.14-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk add --no-cache build-base

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN python -m grpc_tools.protoc \
  -I /app/core/proto \
  --python_out=/app \
  --grpc_python_out=/app \
  /app/core/proto/v2ray_stats_command.proto

RUN chmod +x /app/docker-entrypoint.sh
RUN chmod +x /app/scheduler.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "panel.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
