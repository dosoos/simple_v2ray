import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_rename_core_traffic_user_time_core_traffi_user_id_a3e1a9_idx"),
    ]

    operations = [
        migrations.AddField(
            model_name="node",
            name="token",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                help_text="节点令牌（从节点加入/上报时使用）",
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="node",
            name="enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterModelOptions(
            name="node",
            options={"verbose_name": "节点管理", "verbose_name_plural": "节点管理"},
        ),
        migrations.AddField(
            model_name="proxyuser",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="proxy_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterModelOptions(
            name="proxyuser",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "代理管理",
                "verbose_name_plural": "代理管理",
            },
        ),
    ]

