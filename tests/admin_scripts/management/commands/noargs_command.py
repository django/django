from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test No-args commands"
    requires_system_checks = []

    def handle(self, **options):
        print('EXECUTE: noargs_command options=%s' % sorted(options.items()))
