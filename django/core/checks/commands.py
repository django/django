from django.core.checks import Error, Tags, register


@register(Tags.commands)
def migrate_and_makemigrations_autodetector(**kwargs):
    from django.core.management import get_commands, load_command_class

    commands = get_commands()

    make_migrations = load_command_class(commands["makemigrations"], "makemigrations")
    migrate = load_command_class(commands["migrate"], "migrate")

    if make_migrations.autodetector is not migrate.autodetector:
        return [
            Error(
                "The migrate and makemigrations commands must have the same "
                "autodetector.",
                hint=(
                    f"makemigrations.Command.autodetector is "
                    f"{make_migrations.autodetector.__name__}, but "
                    f"migrate.Command.autodetector is "
                    f"{migrate.autodetector.__name__}."
                ),
                id="commands.E001",
            )
        ]

    return []
