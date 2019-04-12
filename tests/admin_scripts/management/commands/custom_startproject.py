from django.core.management.commands.startproject import Command as BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--extra", help="An arbitrary extra value passed to the context"
        )
