from __future__ import unicode_literals

from django.core.management.base import SQLAppOrModelCommand
from django.core.management.sql import sql_custom
from django.db import connections


class Command(SQLAppOrModelCommand):
    help = "Prints the custom table modifying SQL statements for the given app name(s)."

    def handle_app_config(self, app_config, **options):
        if app_config.models_module is None:
            return
        connection = connections[options.get('database')]
        specific_models = options.get('specific_models')
        statements = sql_custom(app_config, self.style, connection, specific_models)
        return '\n'.join(statements)
