from optparse import make_option

from django.core.management.commands.startproject import Command as BaseCommand


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--extra',
                    action='store', dest='extra',
                    help='An arbitrary extra value passed to the context'),
        )
