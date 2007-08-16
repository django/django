from django.core.management.base import AppCommand

class Command(AppCommand):
    help = 'Prints the SQL statements for resetting sequences for the given app name(s).'
    output_transaction = True

    def handle_app(self, app, **options):
        from django.db import backend, models
        return '\n'.join(backend.get_sql_sequence_reset(self.style, models.get_models(app)))
