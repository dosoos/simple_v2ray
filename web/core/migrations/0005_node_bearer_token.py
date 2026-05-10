import secrets
import uuid

from django.db import migrations, models


def fill_bearer_tokens(apps, schema_editor):
    Node = apps.get_model("core", "Node")
    for n in Node.objects.all():
        if n.is_local:
            continue
        if not n.bearer_token:
            n.bearer_token = secrets.token_urlsafe(48)
            n.save(update_fields=["bearer_token"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_remove_node_key"),
    ]

    operations = [
        migrations.RenameField(
            model_name="node",
            old_name="token",
            new_name="node_uuid",
        ),
        migrations.AlterField(
            model_name="node",
            name="node_uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                help_text="节点固定标识（展示与加入登记），不参与 API 鉴权",
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="node",
            name="bearer_token",
            field=models.CharField(
                blank=True,
                db_index=True,
                editable=False,
                help_text="同步 API 令牌（Authorization: Bearer），后台可撤销",
                max_length=128,
                null=True,
                unique=True,
            ),
        ),
        migrations.RunPython(fill_bearer_tokens, migrations.RunPython.noop),
    ]
