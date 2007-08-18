import django
from optparse import OptionParser
import os
import sys
import textwrap

# For backwards compatibility: get_version() used to be in this module.
get_version = django.get_version

def find_commands(path):
    """
    Given a path to a management directory, return a list of all the command names 
    that are available. Returns an empty list if no commands are defined.
    """
    command_dir = os.path.join(path, 'commands')
    try:
        return [f[:-3] for f in os.listdir(command_dir) if not f.startswith('_') and f.endswith('.py')]
    except OSError:
        return []

def load_command_class(module, name):
    """
    Given a command name, returns the Command class instance. Raises
    Raises ImportError if a command module doesn't exist, or AttributeError
    if a command module doesn't include .
    """
    # Let any errors propogate.
    return getattr(__import__('%s.management.commands.%s' % (module, name), {}, {}, ['Command']), 'Command')()

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
        return dict([(name, load_command_class('django.core',name)) 
                        for name in find_commands(__path__[0])])

    def usage(self):
        """
        Returns a usage string, for use with optparse.

        The string doesn't include the options (e.g., "--verbose"), because
        optparse puts those in automatically.
        """
        usage = ["%prog command [options]\nactions:"]
        commands = self.commands.items()
        commands.sort()
        for name, cmd in commands:
            usage.append('  %s %s' % (name, cmd.args))
            usage.extend(textwrap.wrap(cmd.help, initial_indent='    ', subsequent_indent='    '))
            usage.append('')
        return '\n'.join(usage[:-1]) # Cut off the last list element, an empty space.

    def execute(self, argv=None):
        """
        Parses the given argv from the command line, determines which command
        to run and runs the command.
        """
        if argv is None:
            argv = sys.argv

        # Create the parser object and parse the command-line args.
        # TODO: Ideally each Command class would register its own options for
        # add_option(), but we'd need to figure out how to allow for multiple
        # Commands using the same options. The optparse library gets in the way
        # by checking for conflicts:
        # http://docs.python.org/lib/optparse-conflicts-between-options.html
        parser = OptionParser(usage=self.usage(), version=get_version())
        parser.add_option('--settings',
            help='The Python path to a settings module, e.g. "myproject.settings.main". If this isn\'t provided, the DJANGO_SETTINGS_MODULE environment variable will be used.')
        parser.add_option('--pythonpath',
            help='A directory to add to the Python path, e.g. "/home/djangoprojects/myproject".')
        parser.add_option('--plain', action='store_true', dest='plain',
            help='When using "shell": Tells Django to use plain Python, not IPython.')
        parser.add_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.')
        parser.add_option('--noreload', action='store_false', dest='use_reloader', default=True,
            help='When using "runserver": Tells Django to NOT use the auto-reloader.')
        parser.add_option('--format', default='json', dest='format',
            help='Specifies the output serialization format for fixtures')
        parser.add_option('--indent', default=None, dest='indent',
            type='int', help='Specifies the indent level to use when pretty-printing output')
        parser.add_option('--verbosity', action='store', dest='verbosity', default='1',
            type='choice', choices=['0', '1', '2'],
            help='Verbosity level; 0=minimal output, 1=normal output, 2=all output')
        parser.add_option('--adminmedia', dest='admin_media_path', default='',
            help='When using "runserver": Specifies the directory from which to serve admin media.')
        options, args = parser.parse_args(argv[1:])

        # If the 'settings' or 'pythonpath' options were submitted, activate those.
        if options.settings:
            os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
        if options.pythonpath:
            sys.path.insert(0, options.pythonpath)

        # Run the appropriate command.
        try:
            command_name = args[0]
        except IndexError:
            sys.stderr.write("Type '%s --help' for usage.\n" % os.path.basename(argv[0]))
            sys.exit(1)
        try:
            command = self.commands[command_name]
        except KeyError:
            sys.stderr.write("Unknown command: %r\nType '%s --help' for usage.\n" % (command_name, os.path.basename(argv[0])))
            sys.exit(1)
        command.execute(*args[1:], **options.__dict__)

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

    def default_commands(self):
        """
        Returns a dictionary of instances of all available Command classes.

        This works by looking for and loading all Python modules in the
        django.core.management.commands package. It also looks for a
        management.commands package in each installed application -- if
        a commands package exists, it loads all commands in that application.

        The dictionary is in the format {name: command_instance}.
        """
        from django.db import models

        # Base command set
        commands = super(ProjectManagementUtility, self).default_commands()
        
        # Get commands from all installed apps
        for app in models.get_apps():
            try:
                app_name = '.'.join(app.__name__.split('.')[:-1])
                path = os.path.join(os.path.dirname(app.__file__),'management')
                commands.update(dict([(name, load_command_class(app_name,name)) for name in find_commands(path)]))
            except AttributeError:
                sys.stderr.write("Management command '%s' in application '%s' doesn't contain a Command instance.\n" % (name, app_name))
                sys.exit(1)
        return commands

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
