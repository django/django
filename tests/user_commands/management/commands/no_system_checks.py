from django.core.management.base import BaseCommand


class Command(BaseCommand):
    requires_system_checks = []

    def handle(self, *args, **options):
        pass
