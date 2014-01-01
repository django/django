from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        self.stdout.write('complex_app')
