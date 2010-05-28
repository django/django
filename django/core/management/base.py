"""
Base classes for writing management commands (named commands which can
be executed through ``django-admin.py`` or ``manage.py``).

"""

import os
import sys
from optparse import make_option, OptionParser

import django
from django.core.exceptions import ImproperlyConfigured
from django.core.management.color import color_style
from django.utils.encoding import smart_str

class CommandError(Exception):
    """
    Exception class indicating a problem while executing a management
    command.

    If this exception is raised during the execution of a management
    command, it will be caught and turned into a nicely-printed error
    message to the appropriate output stream (i.e., stderr); as a
    result, raising this exception (with a sensible description of the
    error) is the preferred way to indicate that something has gone
    wrong in the execution of a command.

    """
    pass

def handle_default_options(options):
    """
    Include any default options that all commands should accept here
    so that ManagementUtility can handle them before searching for
    user commands.

    """
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    if options.pythonpath:
        sys.path.insert(0, options.pythonpath)

class BaseCommand(object):
    """
    The base class from which all management commands ultimately
    derive.

    Use this class if you want access to all of the mechanisms which
    parse the command-line arguments and work out what code to call in
    response; if you don't need to change any of that behavior,
    consider using one of the subclasses defined in this file.

    If you are interested in overriding/customizing various aspects of
    the command-parsing and -execution behavior, the normal flow works
    as follows:

    1. ``django-admin.py`` or ``manage.py`` loads the command class
       and calls its ``run_from_argv()`` method.

    2. The ``run_from_argv()`` method calls ``create_parser()`` to get
       an ``OptionParser`` for the arguments, parses them, performs
       any environment changes requested by options like
       ``pythonpath``, and then calls the ``execute()`` method,
       passing the parsed arguments.

    3. The ``execute()`` method attempts to carry out the command by
       calling the ``handle()`` method with the parsed arguments; any
       output produced by ``handle()`` will be printed to standard
       output and, if the command is intended to produce a block of
       SQL statements, will be wrapped in ``BEGIN`` and ``COMMIT``.

    4. If ``handle()`` raised a ``CommandError``, ``execute()`` will
       instead print an error message to ``stderr``.

    Thus, the ``handle()`` method is typically the starting point for
    subclasses; many built-in commands and command types either place
    all of their logic in ``handle()``, or perform some additional
    parsing work in ``handle()`` and then delegate from it to more
    specialized methods as needed.

    Several attributes affect behavior at various steps along the way:

    ``args``
        A string listing the arguments accepted by the command,
        suitable for use in help messages; e.g., a command which takes
        a list of application names might set this to '<appname
        appname ...>'.

    ``can_import_settings``
        A boolean indicating whether the command needs to be able to
        import Django settings; if ``True``, ``execute()`` will verify
        that this is possible before proceeding. Default value is
        ``True``.

    ``help``
        A short description of the command, which will be printed in
        help messages.

    ``option_list``
        This is the list of ``optparse`` options which will be fed
        into the command's ``OptionParser`` for parsing arguments.

    ``output_transaction``
        A boolean indicating whether the command outputs SQL
        statements; if ``True``, the output will automatically be
        wrapped with ``BEGIN;`` and ``COMMIT;``. Default value is
        ``False``.

    ``requires_model_validation``
        A boolean; if ``True``, validation of installed models will be
        performed prior to executing the command. Default value is
        ``True``. To validate an individual application's models
        rather than all applications' models, call
        ``self.validate(app)`` from ``handle()``, where ``app`` is the
        application's Python module.

    """
    # Metadata about this command.
    option_list = (
        make_option('-v', '--verbosity', action='store', dest='verbosity', default='1',
            type='choice', choices=['0', '1', '2'],
            help='Verbosity level; 0=minimal output, 1=normal output, 2=all output'),
        make_option('--settings',
            help='The Python path to a settings module, e.g. "myproject.settings.main". If this isn\'t provided, the DJANGO_SETTINGS_MODULE environment variable will be used.'),
        make_option('--pythonpath',
            help='A directory to add to the Python path, e.g. "/home/djangoprojects/myproject".'),
        make_option('--traceback', action='store_true',
            help='Print traceback on exception'),
    )
    help = ''
    args = ''

    # Configuration shortcuts that alter various logic.
    can_import_settings = True
    requires_model_validation = True
    output_transaction = False # Whether to wrap the output in a "BEGIN; COMMIT;"

    def __init__(self):
        self.style = color_style()

    def get_version(self):
        """
        Return the Django version, which should be correct for all
        built-in Django commands. User-supplied commands should
        override this method.

        """
        return django.get_version()

    def usage(self, subcommand):
        """
        Return a brief description of how to use this command, by
        default from the attribute ``self.help``.

        """
        usage = '%%prog %s [options] %s' % (subcommand, self.args)
        if self.help:
            return '%s\n\n%s' % (usage, self.help)
        else:
            return usage

    def create_parser(self, prog_name, subcommand):
        """
        Create and return the ``OptionParser`` which will be used to
        parse the arguments to this command.

        """
        return OptionParser(prog=prog_name,
                            usage=self.usage(subcommand),
                            version=self.get_version(),
                            option_list=self.option_list)

    def print_help(self, prog_name, subcommand):
        """
        Print the help message for this command, derived from
        ``self.usage()``.

        """
        parser = self.create_parser(prog_name, subcommand)
        parser.print_help()

    def run_from_argv(self, argv):
        """
        Set up any environment changes requested (e.g., Python path
        and Django settings), then run this command.

        """
        parser = self.create_parser(argv[0], argv[1])
        options, args = parser.parse_args(argv[2:])
        handle_default_options(options)
        self.execute(*args, **options.__dict__)

    def execute(self, *args, **options):
        """
        Try to execute this command, performing model validation if
        needed (as controlled by the attribute
        ``self.requires_model_validation``). If the command raises a
        ``CommandError``, intercept it and print it sensibly to
        stderr.

        """
        # Switch to English, because django-admin.py creates database content
        # like permissions, and those shouldn't contain any translations.
        # But only do this if we can assume we have a working settings file,
        # because django.utils.translation requires settings.
        if self.can_import_settings:
            try:
                from django.utils import translation
                translation.activate('en-us')
            except ImportError, e:
                # If settings should be available, but aren't,
                # raise the error and quit.
                sys.stderr.write(smart_str(self.style.ERROR('Error: %s\n' % e)))
                sys.exit(1)
        try:
            if self.requires_model_validation:
                self.validate()
            output = self.handle(*args, **options)
            if output:
                if self.output_transaction:
                    # This needs to be imported here, because it relies on
                    # settings.
                    from django.db import connections, DEFAULT_DB_ALIAS
                    connection = connections[options.get('database', DEFAULT_DB_ALIAS)]
                    if connection.ops.start_transaction_sql():
                        print self.style.SQL_KEYWORD(connection.ops.start_transaction_sql())
                print output
                if self.output_transaction:
                    print self.style.SQL_KEYWORD(connection.ops.end_transaction_sql())
        except CommandError, e:
            sys.stderr.write(smart_str(self.style.ERROR('Error: %s\n' % e)))
            sys.exit(1)

    def validate(self, app=None, display_num_errors=False):
        """
        Validates the given app, raising CommandError for any errors.

        If app is None, then this will validate all installed apps.

        """
        from django.core.management.validation import get_validation_errors
        try:
            from cStringIO import StringIO
        except ImportError:
            from StringIO import StringIO
        s = StringIO()
        num_errors = get_validation_errors(s, app)
        if num_errors:
            s.seek(0)
            error_text = s.read()
            raise CommandError("One or more models did not validate:\n%s" % error_text)
        if display_num_errors:
            print "%s error%s found" % (num_errors, num_errors != 1 and 's' or '')

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.

        """
        raise NotImplementedError()

class AppCommand(BaseCommand):
    """
    A management command which takes one or more installed application
    names as arguments, and does something with each of them.

    Rather than implementing ``handle()``, subclasses must implement
    ``handle_app()``, which will be called once for each application.

    """
    args = '<appname appname ...>'

    def handle(self, *app_labels, **options):
        from django.db import models
        if not app_labels:
            raise CommandError('Enter at least one appname.')
        try:
            app_list = [models.get_app(app_label) for app_label in app_labels]
        except (ImproperlyConfigured, ImportError), e:
            raise CommandError("%s. Are you sure your INSTALLED_APPS setting is correct?" % e)
        output = []
        for app in app_list:
            app_output = self.handle_app(app, **options)
            if app_output:
                output.append(app_output)
        return '\n'.join(output)

    def handle_app(self, app, **options):
        """
        Perform the command's actions for ``app``, which will be the
        Python module corresponding to an application name given on
        the command line.

        """
        raise NotImplementedError()

class LabelCommand(BaseCommand):
    """
    A management command which takes one or more arbitrary arguments
    (labels) on the command line, and does something with each of
    them.

    Rather than implementing ``handle()``, subclasses must implement
    ``handle_label()``, which will be called once for each label.

    If the arguments should be names of installed applications, use
    ``AppCommand`` instead.

    """
    args = '<label label ...>'
    label = 'label'

    def handle(self, *labels, **options):
        if not labels:
            raise CommandError('Enter at least one %s.' % self.label)

        output = []
        for label in labels:
            label_output = self.handle_label(label, **options)
            if label_output:
                output.append(label_output)
        return '\n'.join(output)

    def handle_label(self, label, **options):
        """
        Perform the command's actions for ``label``, which will be the
        string as given on the command line.

        """
        raise NotImplementedError()

class NoArgsCommand(BaseCommand):
    """
    A command which takes no arguments on the command line.

    Rather than implementing ``handle()``, subclasses must implement
    ``handle_noargs()``; ``handle()`` itself is overridden to ensure
    no arguments are passed to the command.

    Attempting to pass arguments will raise ``CommandError``.

    """
    args = ''

    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")
        return self.handle_noargs(**options)

    def handle_noargs(self, **options):
        """
        Perform this command's actions.

        """
        raise NotImplementedError()

def copy_helper(style, app_or_project, name, directory, other_name=''):
    """
    Copies either a Django application layout template or a Django project
    layout template into the specified directory.

    """
    # style -- A color style object (see django.core.management.color).
    # app_or_project -- The string 'app' or 'project'.
    # name -- The name of the application or project.
    # directory -- The directory to which the layout template should be copied.
    # other_name -- When copying an application layout, this should be the name
    #               of the project.
    import re
    import shutil
    other = {'project': 'app', 'app': 'project'}[app_or_project]
    if not re.search(r'^[_a-zA-Z]\w*$', name): # If it's not a valid directory name.
        # Provide a smart error message, depending on the error.
        if not re.search(r'^[_a-zA-Z]', name):
            message = 'make sure the name begins with a letter or underscore'
        else:
            message = 'use only numbers, letters and underscores'
        raise CommandError("%r is not a valid %s name. Please %s." % (name, app_or_project, message))
    top_dir = os.path.join(directory, name)
    try:
        os.mkdir(top_dir)
    except OSError, e:
        raise CommandError(e)

    # Determine where the app or project templates are. Use
    # django.__path__[0] because we don't know into which directory
    # django has been installed.
    template_dir = os.path.join(django.__path__[0], 'conf', '%s_template' % app_or_project)

    for d, subdirs, files in os.walk(template_dir):
        relative_dir = d[len(template_dir)+1:].replace('%s_name' % app_or_project, name)
        if relative_dir:
            os.mkdir(os.path.join(top_dir, relative_dir))
        for i, subdir in enumerate(subdirs):
            if subdir.startswith('.'):
                del subdirs[i]
        for f in files:
            if not f.endswith('.py'):
                # Ignore .pyc, .pyo, .py.class etc, as they cause various
                # breakages.
                continue
            path_old = os.path.join(d, f)
            path_new = os.path.join(top_dir, relative_dir, f.replace('%s_name' % app_or_project, name))
            fp_old = open(path_old, 'r')
            fp_new = open(path_new, 'w')
            fp_new.write(fp_old.read().replace('{{ %s_name }}' % app_or_project, name).replace('{{ %s_name }}' % other, other_name))
            fp_old.close()
            fp_new.close()
            try:
                shutil.copymode(path_old, path_new)
                _make_writeable(path_new)
            except OSError:
                sys.stderr.write(style.NOTICE("Notice: Couldn't set permission bits on %s. You're probably using an uncommon filesystem setup. No problem.\n" % path_new))

def _make_writeable(filename):
    """
    Make sure that the file is writeable. Useful if our source is
    read-only.

    """
    import stat
    if sys.platform.startswith('java'):
        # On Jython there is no os.access()
        return
    if not os.access(filename, os.W_OK):
        st = os.stat(filename)
        new_permissions = stat.S_IMODE(st.st_mode) | stat.S_IWUSR
        os.chmod(filename, new_permissions)
