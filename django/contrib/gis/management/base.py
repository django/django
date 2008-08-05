from django.core.management.base import BaseCommand, CommandError

class ArgsCommand(BaseCommand):
    """
    Command class for commands that take multiple arguments.
    """
    args = '<arg arg ...>'

    def handle(self, *args, **options):
        if not args:
            raise CommandError('Must provide the following arguments: %s' % self.args)
        return self.handle_args(*args, **options)

    def handle_args(self, *args, **options):
        raise NotImplementedError()
