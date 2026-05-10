import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_node_bearer_token"),
    ]

    operations = [
        migrations.AlterField(
            model_name="node",
            name="node_uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                help_text="节点固定标识（展示与加入登记），易被仿冒，仅作名称/配对用",
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="node",
            name="bearer_token",
            field=models.CharField(
                blank=True,
                db_index=True,
                editable=False,
                help_text="同步 API 密钥，请求头 Authorization: Bearer …；撤销后须重新加入",
                max_length=128,
                null=True,
                unique=True,
            ),
        ),
    ]
