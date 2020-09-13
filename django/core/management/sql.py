from django.apps import apps
from django.db import models


def sql_flush(style, connection, reset_sequences=True, allow_cascade=False):
    """
    Return a list of the SQL statements used to flush the database.
    """
    tables = connection.introspection.django_table_names(only_existing=True, include_views=False)
    return connection.ops.sql_flush(
        style,
        tables,
        reset_sequences=reset_sequences,
        allow_cascade=allow_cascade,
    )


def generic_signal_emitter(signal, verbose_message):
    def emit_signal(verbosity, interactive, db, **kwargs):
        # Emit the signal for every application.
        for app_config in apps.get_app_configs():
            if app_config.models_module is None:
                continue
            if verbosity >= 2:
                print(verbose_message % app_config.label)
            signal.send(
                sender=app_config,
                app_config=app_config,
                verbosity=verbosity,
                interactive=interactive,
                using=db,
                **kwargs
            )
    return emit_signal


emit_pre_migrate_signal = generic_signal_emitter(
    models.signals.pre_migrate,
    "Running pre-migrate handlers for application %s"
)

emit_post_migrate_signal = generic_signal_emitter(
    models.signals.post_migrate,
    "Running post-migrate handlers for application %s"
)

emit_pre_migration_signal = generic_signal_emitter(
    models.signals.pre_migration,
    "Running pre-migration handlers for application %s"
)

emit_post_migration_signal = generic_signal_emitter(
    models.signals.post_migration,
    "Running post-migration handlers for application %s"
)
