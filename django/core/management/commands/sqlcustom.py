from django.core.management.base import AppCommand

class Command(AppCommand):
    help = "Prints the custom table modifying SQL statements for the given app name(s)."

    output_transaction = True

    def handle_app(self, app, **options):
        from django.core.management.sql import sql_custom
        return '\n'.join(sql_custom(app))
