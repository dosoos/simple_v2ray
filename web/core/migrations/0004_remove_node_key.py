from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_proxyuser_user_node_token_enabled_and_verbose_names"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="node",
            name="key",
        ),
    ]
