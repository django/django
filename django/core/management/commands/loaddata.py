from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from optparse import make_option
import sys
import os
import bz2, gzip, zipfile

try:
    set
except NameError:
    from sets import Set as set   # Python 2.3 fallback

class Command(BaseCommand):
    help = 'Installs the named fixture(s) in the database.'
    args = "fixture [fixture ...]"

    def handle(self, *fixture_labels, **options):
        from django.db.models import get_apps
        from django.core import serializers
        from django.db import connection, transaction
        from django.conf import settings

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
            transaction.commit_unless_managed()
            transaction.enter_transaction_management()
            transaction.managed(True)

        class SingleZipReader(zipfile.ZipFile):
            def __init__(self, *args, **kwargs):
                zipfile.ZipFile.__init__(self, *args, **kwargs)
                if settings.DEBUG:
                    assert len(self.namelist()) == 1, "Zip-compressed fixtures must contain only one file."
            def read(self):
                return zipfile.ZipFile.read(self, self.namelist()[0])

        compression_types = {
            None:   file,
            'bz2':  bz2.BZ2File,
            'gz':   gzip.GzipFile,
            'zip':  SingleZipReader
        }

        app_fixtures = [os.path.join(os.path.dirname(app.__file__), 'fixtures') for app in get_apps()]
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
                transaction.rollback()
                transaction.leave_transaction_management()
                return

            if os.path.isabs(fixture_name):
                fixture_dirs = [fixture_name]
            else:
                fixture_dirs = app_fixtures + list(settings.FIXTURE_DIRS) + ['']

            for fixture_dir in fixture_dirs:
                if verbosity > 1:
                    print "Checking %s for fixtures..." % humanize(fixture_dir)

                label_found = False
                for format in formats:
                    for compression_format in compression_formats:
                        if compression_format: 
                            file_name = '.'.join([fixture_name, format, 
                                                  compression_format])
                        else: 
                            file_name = '.'.join([fixture_name, format])
                    
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
                                transaction.rollback()
                                transaction.leave_transaction_management()
                                return
                            else:
                                fixture_count += 1
                                if verbosity > 0:
                                    print "Installing %s fixture '%s' from %s." % \
                                        (format, fixture_name, humanize(fixture_dir))
                                try:
                                    objects = serializers.deserialize(format, fixture)
                                    for obj in objects:
                                        object_count += 1
                                        models.add(obj.object.__class__)
                                        obj.save()
                                    label_found = True
                                except (SystemExit, KeyboardInterrupt):
                                    raise
                                except Exception:
                                    import traceback
                                    fixture.close()
                                    transaction.rollback()
                                    transaction.leave_transaction_management()
                                    if show_traceback:
                                        import traceback
                                        traceback.print_exc()
                                    else:
                                        sys.stderr.write(
                                            self.style.ERROR("Problem installing fixture '%s': %s\n" %
                                                 (full_path, traceback.format_exc())))
                                    return
                                fixture.close()
                        except Exception, e:
                            if verbosity > 1:
                                print "No %s fixture '%s' in %s." % \
                                    (format, fixture_name, humanize(fixture_dir))
                                print e
                                transaction.rollback()
                                transaction.leave_transaction_management()
                                return

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
            transaction.commit()
            transaction.leave_transaction_management()

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
