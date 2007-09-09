import django
from optparse import OptionParser
import os
import sys
import textwrap

# For backwards compatibility: get_version() used to be in this module.
get_version = django.get_version

def load_command_class(name):
    """
    Given a command name, returns the Command class instance. Raises
    ImportError if it doesn't exist.
    """
    # Let the ImportError propogate.
    return getattr(__import__('django.core.management.commands.%s' % name, {}, {}, ['Command']), 'Command')()

def call_command(name, *args, **options):
    """
    Calls the given command, with the given options and args/kwargs.

    This is the primary API you should use for calling specific commands.

    Some examples:
        call_command('syncdb')
        call_command('shell', plain=True)
        call_command('sqlall', 'myapp')
    """
    klass = load_command_class(name)
    return klass.execute(*args, **options)

class ManagementUtility(object):
    """
    Encapsulates the logic of the django-admin.py and manage.py utilities.

    A ManagementUtility has a number of commands, which can be manipulated
    by editing the self.commands dictionary.
    """
    def __init__(self):
        self.commands = self.default_commands()

    def default_commands(self):
        """
        Returns a dictionary of instances of all available Command classes.

        This works by looking for and loading all Python modules in the
        django.core.management.commands package.

        The dictionary is in the format {name: command_instance}.
        """
        command_dir = os.path.join(__path__[0], 'commands')
        names = [f[:-3] for f in os.listdir(command_dir) if not f.startswith('_') and f.endswith('.py')]
        return dict([(name, load_command_class(name)) for name in names])

    def print_help(self, argv):
        """
        Returns the help message, as a string.
        """
        prog_name = os.path.basename(argv[0])
        usage = ['%s <subcommand> [options] [args]' % prog_name]
        usage.append('Django command line tool, version %s' % django.get_version())
        usage.append("Type '%s help <subcommand>' for help on a specific subcommand." % prog_name)
        usage.append('Available subcommands:')
        commands = self.commands.keys()
        commands.sort()
        for cmd in commands:
            usage.append('  %s' % cmd)
        print '\n'.join(usage)

    def fetch_command(self, subcommand, command_name):
        """
        Tries to fetch the given subcommand, printing a message with the
        appropriate command called from the command line (usually
        django-admin.py or manage.py) if it can't be found.
        """
        try:
            return self.commands[subcommand]
        except KeyError:
            sys.stderr.write("Unknown command: %r\nType '%s help' for usage.\n" % (subcommand, command_name))
            sys.exit(1)

    def execute(self, argv=None):
        """
        Figures out which command is being run (the first arg), creates a parser
        appropriate to that command, and runs it.
        """
        if argv is None:
            argv = sys.argv
        try:
            command_name = argv[1]
        except IndexError:
            sys.stderr.write("Type '%s help' for usage.\n" % os.path.basename(argv[0]))
            sys.exit(1)

        if command_name == 'help':
            if len(argv) > 2:
                self.fetch_command(argv[2], argv[0]).print_help(argv[2:])
            else:
                self.print_help(argv)
        # Special-cases: We want 'django-admin.py --version' and
        # 'django-admin.py --help' to work, for backwards compatibility.
        elif argv[1:] == ['--version']:
            print django.get_version()
        elif argv[1:] == ['--help']:
            self.print_help(argv)
        else:
            self.fetch_command(command_name, argv[0]).run(argv[1:])

class ProjectManagementUtility(ManagementUtility):
    """
    A ManagementUtility that is specific to a particular Django project.
    As such, its commands are slightly different than those of its parent
    class.

    In practice, this class represents manage.py, whereas ManagementUtility
    represents django-admin.py.
    """
    def __init__(self, project_directory):
        super(ProjectManagementUtility, self).__init__()

        # Remove the "startproject" command from self.commands, because
        # that's a django-admin.py command, not a manage.py command.
        del self.commands['startproject']

        # Override the startapp command so that it always uses the
        # project_directory, not the current working directory (which is default).
        from django.core.management.commands.startapp import ProjectCommand
        self.commands['startapp'] = ProjectCommand(project_directory)

def setup_environ(settings_mod):
    """
    Configure the runtime environment. This can also be used by external
    scripts wanting to set up a similar environment to manage.py.
    """
    # Add this project to sys.path so that it's importable in the conventional
    # way. For example, if this file (manage.py) lives in a directory
    # "myproject", this code would add "/path/to/myproject" to sys.path.
    project_directory, settings_filename = os.path.split(settings_mod.__file__)
    project_name = os.path.basename(project_directory)
    settings_name = os.path.splitext(settings_filename)[0]
    sys.path.append(os.path.join(project_directory, '..'))
    project_module = __import__(project_name, {}, {}, [''])
    sys.path.pop()

    # Set DJANGO_SETTINGS_MODULE appropriately.
    os.environ['DJANGO_SETTINGS_MODULE'] = '%s.%s' % (project_name, settings_name)
    return project_directory

def execute_from_command_line(argv=None):
    """
    A simple method that runs a ManagementUtility.
    """
    utility = ManagementUtility()
    utility.execute(argv)

def execute_manager(settings_mod, argv=None):
    """
    Like execute_from_command_line(), but for use by manage.py, a
    project-specific django-admin.py utility.
    """
    project_directory = setup_environ(settings_mod)
    utility = ProjectManagementUtility(project_directory)
    utility.execute(argv)
