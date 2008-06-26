from django.core.management.base import AppCommand

class Command(AppCommand):
    help = "Prints the CREATE TABLE, custom SQL and CREATE INDEX SQL statements for the given model module name(s)."

    output_transaction = True

    def handle_app(self, app, **options):
        from django.core.management.sql import sql_all
        return u'\n'.join(sql_all(app, self.style)).encode('utf-8')
