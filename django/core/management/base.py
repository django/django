from django.core.exceptions import ImproperlyConfigured
from django.core.management.color import color_style
import sys
import os

class CommandError(Exception):
    pass

class BaseCommand(object):
    # Metadata about this command.
    help = ''
    args = ''

    # Configuration shortcuts that alter various logic.
    can_import_settings = True
    requires_model_validation = True
    output_transaction = False # Whether to wrap the output in a "BEGIN; COMMIT;"

    def __init__(self):
        self.style = color_style()

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
    args = '[appname ...]'

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
    args = '[label ...]'
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
        from django.db import models
        if len(args) != 0:
            raise CommandError("Command doesn't accept any arguments")

        return self.handle_noargs(**options)

    def handle_noargs(self, **options):
        raise NotImplementedError()

def copy_helper(style, app_or_project, name, directory, other_name=''):
    import django
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
    if not os.access(filename, os.W_OK):
      st = os.stat(filename)
      new_permissions = stat.S_IMODE(st.st_mode) | stat.S_IWUSR
      os.chmod(filename, new_permissions)

