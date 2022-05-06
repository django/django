import datetime
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Device",
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
                    "name",
                    models.CharField(
                        choices=[("TOTP", "TOTP"), ("SMS", "SMS"), ("EMAIL", "EMAIL")],
                        max_length=5,
                        verbose_name="name",
                    ),
                ),
                (
                    "initial_time",
                    models.DateTimeField(
                        default=datetime.datetime(
                            1970, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                        ),
                        verbose_name="initial time",
                    ),
                ),
                ("key", models.CharField(max_length=40, verbose_name="key")),
                (
                    "digits",
                    models.PositiveSmallIntegerField(default=6, verbose_name="digits"),
                ),
                (
                    "time_step",
                    models.PositiveSmallIntegerField(
                        default=30, verbose_name="time step"
                    ),
                ),
                (
                    "failed_attempts",
                    models.PositiveSmallIntegerField(
                        default=0, verbose_name="failed attempts"
                    ),
                ),
                (
                    "try_later",
                    models.DateTimeField(auto_now_add=True, verbose_name="try later"),
                ),
                (
                    "slug",
                    models.UUIDField(
                        default=uuid.uuid4, unique=True, verbose_name="slug"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="updated at"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
            ],
            options={
                "verbose_name": "device",
                "verbose_name_plural": "devices",
            },
        ),
        migrations.AddConstraint(
            model_name="device",
            constraint=models.UniqueConstraint(
                fields=("user", "name"), name="unique_device"
            ),
        ),
    ]
