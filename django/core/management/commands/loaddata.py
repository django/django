import sys
import os
import gzip
import zipfile
from optparse import make_option

from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import connections, transaction, DEFAULT_DB_ALIAS
from django.db.models import get_apps
from django.utils.itercompat import product

try:
    set
except NameError:
    from sets import Set as set   # Python 2.3 fallback

try:
    import bz2
    has_bz2 = True
except ImportError:
    has_bz2 = False

class Command(BaseCommand):
    help = 'Installs the named fixture(s) in the database.'
    args = "fixture [fixture ...]"

    option_list = BaseCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a specific database to load '
                'fixtures into. Defaults to the "default" database.'),
        make_option('-e', '--exclude', dest='exclude',action='append', default=[],
            help='App to exclude (use multiple --exclude to exclude multiple apps).'),
    )

    def handle(self, *fixture_labels, **options):
        using = options.get('database', DEFAULT_DB_ALIAS)
        excluded_apps = options.get('exclude', [])

        connection = connections[using]
        self.style = no_style()

        verbosity = int(options.get('verbosity', 1))
        show_traceback = options.get('traceback', False)

        # commit is a stealth option - it isn't really useful as
        # a command line option, but it can be useful when invoking
        # loaddata from within another script.
        # If commit=True, loaddata will use its own transaction;
        # if commit=False, the data load SQL will become part of
        # the transaction in place when loaddata was invoked.
        commit = options.get('commit', True)

        # Keep a count of the installed objects and fixtures
        fixture_count = 0
        object_count = 0
        models = set()

        humanize = lambda dirname: dirname and "'%s'" % dirname or 'absolute path'

        # Get a cursor (even though we don't need one yet). This has
        # the side effect of initializing the test database (if
        # it isn't already initialized).
        cursor = connection.cursor()

        # Start transaction management. All fixtures are installed in a
        # single transaction to ensure that all references are resolved.
        if commit:
            transaction.commit_unless_managed(using=using)
            transaction.enter_transaction_management(using=using)
            transaction.managed(True, using=using)

        class SingleZipReader(zipfile.ZipFile):
            def __init__(self, *args, **kwargs):
                zipfile.ZipFile.__init__(self, *args, **kwargs)
                if settings.DEBUG:
                    assert len(self.namelist()) == 1, "Zip-compressed fixtures must contain only one file."
            def read(self):
                return zipfile.ZipFile.read(self, self.namelist()[0])

        compression_types = {
            None:   file,
            'gz':   gzip.GzipFile,
            'zip':  SingleZipReader
        }
        if has_bz2:
            compression_types['bz2'] = bz2.BZ2File

        app_module_paths = []
        for app in get_apps():
            if hasattr(app, '__path__'):
                # It's a 'models/' subpackage
                for path in app.__path__:
                    app_module_paths.append(path)
            else:
                # It's a models.py module
                app_module_paths.append(app.__file__)

        app_fixtures = [os.path.join(os.path.dirname(path), 'fixtures') for path in app_module_paths]
        for fixture_label in fixture_labels:
            parts = fixture_label.split('.')

            if len(parts) > 1 and parts[-1] in compression_types:
                compression_formats = [parts[-1]]
                parts = parts[:-1]
            else:
                compression_formats = compression_types.keys()

            if len(parts) == 1:
                fixture_name = parts[0]
                formats = serializers.get_public_serializer_formats()
            else:
                fixture_name, format = '.'.join(parts[:-1]), parts[-1]
                if format in serializers.get_public_serializer_formats():
                    formats = [format]
                else:
                    formats = []

            if formats:
                if verbosity > 1:
                    print "Loading '%s' fixtures..." % fixture_name
            else:
                sys.stderr.write(
                    self.style.ERROR("Problem installing fixture '%s': %s is not a known serialization format." %
                        (fixture_name, format)))
                transaction.rollback(using=using)
                transaction.leave_transaction_management(using=using)
                return

            if os.path.isabs(fixture_name):
                fixture_dirs = [fixture_name]
            else:
                fixture_dirs = app_fixtures + list(settings.FIXTURE_DIRS) + ['']

            for fixture_dir in fixture_dirs:
                if verbosity > 1:
                    print "Checking %s for fixtures..." % humanize(fixture_dir)

                label_found = False
                for combo in product([using, None], formats, compression_formats):
                    database, format, compression_format = combo
                    file_name = '.'.join(
                        p for p in [
                            fixture_name, database, format, compression_format
                        ]
                        if p
                    )

                    if verbosity > 1:
                        print "Trying %s for %s fixture '%s'..." % \
                            (humanize(fixture_dir), file_name, fixture_name)
                    full_path = os.path.join(fixture_dir, file_name)
                    open_method = compression_types[compression_format]
                    try:
                        fixture = open_method(full_path, 'r')
                        if label_found:
                            fixture.close()
                            print self.style.ERROR("Multiple fixtures named '%s' in %s. Aborting." %
                                (fixture_name, humanize(fixture_dir)))
                            transaction.rollback(using=using)
                            transaction.leave_transaction_management(using=using)
                            return
                        else:
                            fixture_count += 1
                            objects_in_fixture = 0
                            if verbosity > 0:
                                print "Installing %s fixture '%s' from %s." % \
                                    (format, fixture_name, humanize(fixture_dir))
                            try:
                                objects = serializers.deserialize(format, fixture, using=using)
                                for obj in objects:
                                    if obj.object._meta.app_label not in excluded_apps:
                                        objects_in_fixture += 1
                                        models.add(obj.object.__class__)
                                        obj.save(using=using)
                                object_count += objects_in_fixture
                                label_found = True
                            except (SystemExit, KeyboardInterrupt):
                                raise
                            except Exception:
                                import traceback
                                fixture.close()
                                transaction.rollback(using=using)
                                transaction.leave_transaction_management(using=using)
                                if show_traceback:
                                    traceback.print_exc()
                                else:
                                    sys.stderr.write(
                                        self.style.ERROR("Problem installing fixture '%s': %s\n" %
                                             (full_path, ''.join(traceback.format_exception(sys.exc_type,
                                                 sys.exc_value, sys.exc_traceback)))))
                                return
                            fixture.close()

                            # If the fixture we loaded contains 0 objects, assume that an
                            # error was encountered during fixture loading.
                            if objects_in_fixture == 0:
                                sys.stderr.write(
                                    self.style.ERROR("No fixture data found for '%s'. (File format may be invalid.)" %
                                        (fixture_name)))
                                transaction.rollback(using=using)
                                transaction.leave_transaction_management(using=using)
                                return

                    except Exception, e:
                        if verbosity > 1:
                            print "No %s fixture '%s' in %s." % \
                                (format, fixture_name, humanize(fixture_dir))

        # If we found even one object in a fixture, we need to reset the
        # database sequences.
        if object_count > 0:
            sequence_sql = connection.ops.sequence_reset_sql(self.style, models)
            if sequence_sql:
                if verbosity > 1:
                    print "Resetting sequences"
                for line in sequence_sql:
                    cursor.execute(line)

        if commit:
            transaction.commit(using=using)
            transaction.leave_transaction_management(using=using)

        if object_count == 0:
            if verbosity > 1:
                print "No fixtures found."
        else:
            if verbosity > 0:
                print "Installed %d object(s) from %d fixture(s)" % (object_count, fixture_count)

        # Close the DB connection. This is required as a workaround for an
        # edge case in MySQL: if the same connection is used to
        # create tables, load data, and query, the query can return
        # incorrect results. See Django #7572, MySQL #37735.
        if commit:
            connection.close()
