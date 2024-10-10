from django.core.management.commands.makemigrations import (
    Command as MakeMigrationsCommand,
)


class Command(MakeMigrationsCommand):
    autodetector_class = int  # intended to cause a healthcheck failure
