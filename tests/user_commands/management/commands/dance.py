from optparse import make_option

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Dance around like a madman."
    args = ''
    requires_model_validation = True

    option_list = BaseCommand.option_list + (
        make_option("-s", "--style", default="Rock'n'Roll"),
        make_option("-x", "--example")
    )

    def handle(self, *args, **options):
        example = options["example"]
        if example == "raise":
            raise CommandError()
        self.stdout.write("I don't feel like dancing %s." % options["style"])
