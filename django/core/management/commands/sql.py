from django.core.management.base import AppCommand

class Command(AppCommand):
    help = "Prints the CREATE TABLE SQL statements for the given app name(s)."

    output_transaction = True

    def handle_app(self, app, **options):
        from django.core.management.sql import sql_create
        return '\n'.join(sql_create(app, self.style))
