from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Returns a list of the SQL statements required to return all tables in the database to the state they were in just after they were installed."

    output_transaction = True

    def handle(self, **options):
        from django.core.management.sql import sql_flush
        return '\n'.join(sql_flush(self.style))
