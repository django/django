import os
import sys
from optparse import make_option, OptionParser

import django
from django.core.exceptions import ImproperlyConfigured
from django.core.management.color import color_style

try:
    set
except NameError:
    from sets import Set as set     # For Python 2.3

class CommandError(Exception):
    pass

def handle_default_options(options):
    """
    Include any default options that all commands should accept
    here so that ManagementUtility can handle them before searching
    for user commands.
    """
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    if options.pythonpath:
        sys.path.insert(0, options.pythonpath)

class BaseCommand(object):
    # Metadata about this command.
    option_list = (
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
        Returns the Django version, which should be correct for all built-in
        Django commands. User-supplied commands should override this method.
        """
        return django.get_version()

    def usage(self, subcommand):
        usage = '%%prog %s [options] %s' % (subcommand, self.args)
        if self.help:
            return '%s\n\n%s' % (usage, self.help)
        else:
            return usage

    def create_parser(self, prog_name, subcommand):
        return OptionParser(prog=prog_name,
                            usage=self.usage(subcommand),
                            version=self.get_version(),
                            option_list=self.option_list)

    def print_help(self, prog_name, subcommand):
        parser = self.create_parser(prog_name, subcommand)
        parser.print_help()

    def run_from_argv(self, argv):
        parser = self.create_parser(argv[0], argv[1])
        options, args = parser.parse_args(argv[2:])
        handle_default_options(options)
        self.execute(*args, **options.__dict__)

    def execute(self, *args, **options):
        # Switch to English, because django-admin.py creates database content
        # like permissions, and those shouldn't contain any translations.
        # But only do this if we can assume we have a working settings file,
        # because django.utils.translation requires settings.
        if self.can_import_settings:
            from django.utils import translation
            translation.activate('en-us')

        try:
            if self.requires_model_validation:
                self.validate()
            output = self.handle(*args, **options)
            if output:
                if self.output_transaction:
                    # This needs to be imported here, because it relies on settings.
                    from django.db import connection
                    if connection.ops.start_transaction_sql():
                        print self.style.SQL_KEYWORD(connection.ops.start_transaction_sql())
                print output
                if self.output_transaction:
                    print self.style.SQL_KEYWORD("COMMIT;")
        except CommandError, e:
            sys.stderr.write(self.style.ERROR(str('Error: %s\n' % e)))
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
        raise NotImplementedError()

class AppCommand(BaseCommand):
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
        raise NotImplementedError()

class LabelCommand(BaseCommand):
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
        raise NotImplementedError()

class NoArgsCommand(BaseCommand):
    args = ''

    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")
        return self.handle_noargs(**options)

    def handle_noargs(self, **options):
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
    if not re.search(r'^\w+$', name): # If it's not a valid directory name.
        raise CommandError("%r is not a valid %s name. Please use only numbers, letters and underscores." % (name, app_or_project))
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
            if f.endswith('.pyc'):
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
    "Makes sure that the file is writeable. Useful if our source is read-only."
    import stat
    if sys.platform.startswith('java'):
        # On Jython there is no os.access()
        return
    if not os.access(filename, os.W_OK):
        st = os.stat(filename)
        new_permissions = stat.S_IMODE(st.st_mode) | stat.S_IWUSR
        os.chmod(filename, new_permissions)
