# Generated migration for contact app

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ContactMessage",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200, verbose_name="name")),
                ("email", models.EmailField(max_length=254, verbose_name="email")),
                ("message", models.TextField(verbose_name="message")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="created at"),
                ),
            ],
            options={
                "verbose_name": "contact message",
                "verbose_name_plural": "contact messages",
                "db_table": "django_contact_message",
                "ordering": ["-created_at"],
            },
        ),
    ]
