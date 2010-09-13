from optparse import make_option
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Dance around like a madman."
    args = ''
    requires_model_validation = True

    option_list =[
        make_option("-s", "--style", default="Rock'n'Roll")
    ]

    def handle(self, *args, **options):
        self.stdout.write("I don't feel like dancing %s." % options["style"])
