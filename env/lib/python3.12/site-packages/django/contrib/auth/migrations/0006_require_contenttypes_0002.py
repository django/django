from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0005_alter_user_last_login_null"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        # Ensure the contenttypes migration is applied before sending
        # post_migrate signals (which create ContentTypes).
    ]
