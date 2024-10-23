from django.core.management.commands.makemigrations import (
    Command as MakeMigrationsCommand,
)


class Command(MakeMigrationsCommand):
    autodetector = int
