from django.core.management.base import NoArgsCommand
from django.utils import timezone


class Command(NoArgsCommand):
    help = "Clean expired sessions."

    def handle_noargs(self, **options):
        from django.db import transaction
        from django.contrib.sessions.models import Session
        Session.objects.filter(expire_date__lt=timezone.now()).delete()
        transaction.commit_unless_managed()
