from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Dance around like a madman."
    args = ''
    requires_system_checks = True

    def add_arguments(self, parser):
        parser.add_argument("integer", nargs='?', type=int, default=0)
        parser.add_argument("-s", "--style", default="Rock'n'Roll")
        parser.add_argument("-x", "--example")
        parser.add_argument("--opt-3", action='store_true', dest='option3')

    def handle(self, *args, **options):
        example = options["example"]
        if example == "raise":
            raise CommandError(returncode=3)
        if options['verbosity'] > 0:
            self.stdout.write("I don't feel like dancing %s." % options["style"])
            self.stdout.write(','.join(options))
        if options['integer'] > 0:
            self.stdout.write("You passed %d as a positional argument." % options['integer'])
