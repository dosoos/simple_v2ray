import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GlobalRevision",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("revision", models.PositiveIntegerField(default=1)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "全局同步版本",
                "verbose_name_plural": "全局同步版本",
            },
        ),
        migrations.CreateModel(
            name="SyncCursor",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("last_user_revision", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "同步游标",
                "verbose_name_plural": "同步游标",
            },
        ),
        migrations.CreateModel(
            name="Node",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "key",
                    models.CharField(
                        db_index=True,
                        help_text="节点标识（当前写死 node-1，后续可扩展）",
                        max_length=64,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=128)),
                (
                    "role",
                    models.CharField(
                        choices=[("master", "主节点"), ("slave", "从节点")],
                        default="master",
                        max_length=16,
                    ),
                ),
                (
                    "base_url",
                    models.URLField(blank=True, help_text="本面板对外访问地址，可选"),
                ),
                ("last_heartbeat", models.DateTimeField(blank=True, null=True)),
                ("is_local", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "节点",
                "verbose_name_plural": "节点",
            },
        ),
        migrations.CreateModel(
            name="ProxyUser",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "label",
                    models.CharField(
                        help_text="对应 V2Ray 客户端 email 字段，用于统计匹配",
                        max_length=128,
                    ),
                ),
                ("alter_id", models.PositiveSmallIntegerField(default=0)),
                ("level", models.PositiveSmallIntegerField(default=0)),
                ("enabled", models.BooleanField(default=True)),
                (
                    "traffic_limit_bytes",
                    models.BigIntegerField(
                        blank=True,
                        help_text="可选流量上限（字节），仅展示/扩展用，当前不强制断开",
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "代理用户",
                "verbose_name_plural": "代理用户",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="TrafficSnapshot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("recorded_at", models.DateTimeField(db_index=True)),
                ("uplink_bytes", models.BigIntegerField()),
                ("downlink_bytes", models.BigIntegerField()),
                (
                    "node",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="traffic_snapshots",
                        to="core.node",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="traffic_snapshots",
                        to="core.proxyuser",
                    ),
                ),
            ],
            options={
                "verbose_name": "流量快照",
                "verbose_name_plural": "流量快照",
                "ordering": ["-recorded_at"],
            },
        ),
        migrations.AddIndex(
            model_name="trafficsnapshot",
            index=models.Index(fields=["user", "recorded_at"], name="core_traffic_user_time"),
        ),
    ]

