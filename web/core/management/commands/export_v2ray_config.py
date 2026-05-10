import json
from pathlib import Path

from django.core.management.base import BaseCommand

from core import config
from core.models import ProxyUser
from core.utils import build_v2ray_config_dict


class Command(BaseCommand):
    help = "根据数据库代理用户导出 V2Ray config.json"

    def handle(self, *args, **options):
        users = list(ProxyUser.objects.all())
        cfg = build_v2ray_config_dict(users)
        path = Path(config.V2RAY_EXPORT_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"已写入 {path}"))

