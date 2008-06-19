from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    help = "Returns a list of the SQL statements required to return all tables in the database to the state they were in just after they were installed."

    output_transaction = True

    def handle_noargs(self, **options):
        from django.core.management.sql import sql_flush
        return u'\n'.join(sql_flush(self.style, only_django=True)).encode('utf-8')
