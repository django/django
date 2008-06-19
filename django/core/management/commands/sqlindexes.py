from django.core.management.base import AppCommand

class Command(AppCommand):
    help = "Prints the CREATE INDEX SQL statements for the given model module name(s)."

    output_transaction = True

    def handle_app(self, app, **options):
        from django.core.management.sql import sql_indexes
        return u'\n'.join(sql_indexes(app, self.style)).encode('utf-8')
