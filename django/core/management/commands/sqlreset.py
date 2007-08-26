from django.core.management.base import AppCommand

class Command(AppCommand):
    help = "Prints the DROP TABLE SQL, then the CREATE TABLE SQL, for the given app name(s)."

    output_transaction = True

    def handle_app(self, app, **options):
        from django.core.management.sql import sql_reset
        return '\n'.join(sql_reset(app, self.style))
