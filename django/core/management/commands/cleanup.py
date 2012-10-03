from django.core import management
from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = "Can be run as a cronjob or directly to clean out old data from the database (only expired sessions at the moment)."

    def handle_noargs(self, **options):
        management.call_command('cleansessions', **options)
