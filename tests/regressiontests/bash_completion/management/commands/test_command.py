import sys, os
from optparse import OptionParser, make_option

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("--list", action="store_true", dest="list",
                    help="Print all options"),
    )

    def handle(self, *args, **options):
        pass
