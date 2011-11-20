from django.core.management.base import NoArgsCommand
from django.utils import timezone

class Command(NoArgsCommand):
    help = "Can be run as a cronjob or directly to clean out old data from the database (only expired sessions at the moment)."

    def handle_noargs(self, **options):
        from django.db import transaction
        from django.contrib.sessions.models import Session
        Session.objects.filter(expire_date__lt=timezone.now()).delete()
        transaction.commit_unless_managed()
