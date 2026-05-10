#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py collectstatic --noinput 2>/dev/null || true
python manage.py export_v2ray_config 2>/dev/null || true
exec "$@"
