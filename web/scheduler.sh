#!/usr/bin/env sh
set -eu

# 简易定时器：避免引入 Celery/Redis，保持项目最小化
# 通过 sleep 周期性执行 Django management commands

INTERVAL="${SCHEDULER_INTERVAL:-300}"

sleep 15
while true; do
  python manage.py collect_v2ray_stats || true
  python manage.py export_v2ray_config || true
  python manage.py sync_from_master || true
  python manage.py push_traffic_to_master || true
  sleep "$INTERVAL"
done

