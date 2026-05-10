from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="trafficsnapshot",
            new_name="core_traffi_user_id_a3e1a9_idx",
            old_name="core_traffic_user_time",
        ),
    ]

