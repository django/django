from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = "Test No-args commands"
    requires_system_checks = False

    def handle_noargs(self, **options):
        print('EXECUTE:NoArgsCommand options=%s' % sorted(options.items()))
