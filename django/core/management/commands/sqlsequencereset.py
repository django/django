from django.core.management.base import AppCommand

class Command(AppCommand):
    help = 'Prints the SQL statements for resetting sequences for the given app name(s).'
    output_transaction = True

    def handle_app(self, app, **options):
        from django.db import connection, models
        return u'\n'.join(connection.ops.sequence_reset_sql(self.style, models.get_models(app))).encode('utf-8')
