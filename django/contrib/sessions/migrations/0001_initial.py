import django.contrib.sessions.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Session",
            fields=[
                (
                    "session_key",
                    models.CharField(
                        max_length=40,
                        serialize=False,
                        verbose_name="session key",
                        primary_key=True,
                    ),
                ),
                ("session_data", models.TextField(verbose_name="session data")),
                (
                    "expire_date",
                    models.DateTimeField(verbose_name="expire date", db_index=True),
                ),
            ],
            options={
                "abstract": False,
                "db_table": "django_session",
                "verbose_name": "session",
                "verbose_name_plural": "sessions",
            },
            managers=[
                ("objects", django.contrib.sessions.models.SessionManager()),
            ],
        ),
    ]
