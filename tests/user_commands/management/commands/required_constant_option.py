from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--append_const",
            action="append_const",
            const=42,
            required=True,
        )
        parser.add_argument("--const", action="store_const", const=31, required=True)
        parser.add_argument("--count", action="count", required=True)
        parser.add_argument("--flag_false", action="store_false", required=True)
        parser.add_argument("--flag_true", action="store_true", required=True)

    def handle(self, *args, **options):
        for option, value in options.items():
            if value is not None:
                self.stdout.write("%s=%s" % (option, value))
