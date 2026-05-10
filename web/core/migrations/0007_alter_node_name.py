from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_alter_node_help_texts"),
    ]

    operations = [
        migrations.AlterField(
            model_name="node",
            name="name",
            field=models.CharField(help_text="节点显示名称", max_length=128),
        ),
    ]
