FROM python:3.14-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN apk add --no-cache docker-cli \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY main.py v2ray_config.py /app/
COPY templates /app/templates/
COPY sneat-1.0.0/assets /app/sneat-1.0.0/assets

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
