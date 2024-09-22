from django.core.checks import Error, Tags, register


@register(Tags.migrations)
def migrate_and_migrations_share_same_autodetector(app_configs, **kwargs):
    from django.core.management import get_commands, load_command_class

    commands = get_commands()

    makemigrations_path = commands.get("makemigrations")
    migrate_path = commands.get("migrate")

    if not makemigrations_path or not migrate_path:
        return []

    MakeMigrationsCommand = load_command_class(makemigrations_path, "makemigrations")
    MigrateCommand = load_command_class(migrate_path, "migrate")

    make_migrations_autodetector = MakeMigrationsCommand.autodetector_class
    migrate_autodetector = MigrateCommand.autodetector_class

    errors = []

    if make_migrations_autodetector is not migrate_autodetector:
        errors.append(
            Error(
                "Migrate and makemigrations don't share the same autodetector class. Currently, this behavior is not supported.",
                hint="makemigrations.Command.autodetector_class is {}, but "
                "migrate.Command.autodetector_class is {}.".format(
                    make_migrations_autodetector, migrate_autodetector
                ),
                id="migrations.E001",
            )
        )

    return errors
