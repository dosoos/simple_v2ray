FROM python:3.14-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN apk add --no-cache docker-cli \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY main.py v2ray_config.py v2ray_stats.py share_links.py traffic_store.py traffic_poller.py stats_command_pb2.py stats_command_pb2_grpc.py /app/
COPY templates /app/templates/
COPY sneat-1.0.0/assets /app/sneat-1.0.0/assets

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
