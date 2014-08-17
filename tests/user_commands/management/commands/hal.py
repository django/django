from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Useless command."

    def add_arguments(self, parser):
        parser.add_argument('args', metavar='app_label', nargs='*',
            help='Specify the app label(s) to works on.')
        parser.add_argument('--empty', action='store_true', dest='empty', default=False,
            help="Do nothing.")

    def handle(self, *app_labels, **options):
        app_labels = set(app_labels)

        if options['empty']:
            self.stdout.write("Dave, I can't do that.")
            return

        if not app_labels:
            raise CommandError("I'm sorry Dave, I'm afraid I can't do that.")

        # raise an error if some --parameter is flowing from options to args
        for app_label in app_labels:
            if app_label.startswith('--'):
                raise CommandError("Sorry, Dave, I can't let you do that.")

        self.stdout.write("Dave, my mind is going. I can feel it. I can feel it.")
