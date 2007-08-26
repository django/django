from django.core.management.base import AppCommand

class Command(AppCommand):
    help = "Prints the DROP TABLE SQL statements for the given app name(s)."

    output_transaction = True

    def handle_app(self, app, **options):
        from django.core.management.sql import sql_delete
        return '\n'.join(sql_delete(app, self.style))
