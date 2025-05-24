import functools
import glob
import gzip
import os
import sys
import warnings
import zipfile
from itertools import product

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.core.management.utils import parse_apps_and_model_labels
from django.db import (
    DEFAULT_DB_ALIAS,
    DatabaseError,
    IntegrityError,
    connections,
    router,
    transaction,
)
from django.utils.functional import cached_property

try:
    import bz2

    has_bz2 = True
except ImportError:
    has_bz2 = False

try:
    import lzma

    has_lzma = True
except ImportError:
    has_lzma = False

READ_STDIN = "-"


class Command(BaseCommand):
    help = "Installs the named fixture(s) in the database."
    missing_args_message = (
        "No database fixture specified. Please provide the path of at least "
        "one fixture in the command line."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "args", metavar="fixture", nargs="+", help="Fixture labels."
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            choices=tuple(connections),
            help=(
                "Nominates a specific database to load fixtures into. Defaults to the "
                '"default" database.'
            ),
        )
        parser.add_argument(
            "--disable-atomic",
            action="store_true",
            help="do not use transaction.atomic duration save data",
        )
        parser.add_argument(
            "--app",
            dest="app_label",
            help="Only look for fixtures in the specified app.",
        )
        parser.add_argument(
            "--ignorenonexistent",
            "-i",
            action="store_true",
            dest="ignore",
            help="Ignores entries in the serialized data for fields that do not "
            "currently exist on the model.",
        )
        parser.add_argument(
            "-e",
            "--exclude",
            action="append",
            default=[],
            help=(
                "An app_label or app_label.ModelName to exclude. Can be used multiple "
                "times."
            ),
        )
        parser.add_argument(
            "--format",
            help="Format of serialized data when reading from stdin.",
        )

    def handle(self, *fixture_labels, **options):
        self.ignore = options["ignore"]
        self.using = options["database"]
        self.app_label = options["app_label"]
        self.verbosity = options["verbosity"]
        self.excluded_models, self.excluded_apps = parse_apps_and_model_labels(
            options["exclude"]
        )
        self.format = options["format"]

        if options["disable_atomic"]:
            self.loaddata(fixture_labels)
        else:
            with transaction.atomic(using=self.using):
                self.loaddata(fixture_labels)

        # Close the DB connection -- unless we're still in a transaction. This
        # is required as a workaround for an edge case in MySQL: if the same
        # connection is used to create tables, load data, and query, the query
        # can return incorrect results. See Django #7572, MySQL #37735.
        if transaction.get_autocommit(self.using):
            connections[self.using].close()

    @cached_property
    def compression_formats(self):
        """A dict mapping format names to (open function, mode arg) tuples."""
        # Forcing binary mode may be revisited after dropping Python 2 support
        # (see #22399).
        compression_formats = {
            None: (open, "rb"),
            "gz": (gzip.GzipFile, "rb"),
            "zip": (SingleZipReader, "r"),
            "stdin": (lambda *args: sys.stdin, None),
        }
        if has_bz2:
            compression_formats["bz2"] = (bz2.BZ2File, "r")
        if has_lzma:
            compression_formats["lzma"] = (lzma.LZMAFile, "r")
            compression_formats["xz"] = (lzma.LZMAFile, "r")
        return compression_formats

    def reset_sequences(self, connection, models):
        """Reset database sequences for the given connection and models."""
        sequence_sql = connection.ops.sequence_reset_sql(no_style(), models)
        if sequence_sql:
            if self.verbosity >= 2:
                self.stdout.write("Resetting sequences")
            with connection.cursor() as cursor:
                for line in sequence_sql:
                    cursor.execute(line)

    def loaddata(self, fixture_labels):
        connection = connections[self.using]

        # Keep a count of the installed objects and fixtures
        self.fixture_count = 0
        self.loaded_object_count = 0
        self.fixture_object_count = 0
        self.models = set()

        self.serialization_formats = serializers.get_public_serializer_formats()

        # Django's test suite repeatedly tries to load initial_data fixtures
        # from apps that don't have any fixtures. Because disabling constraint
        # checks can be expensive on some database (especially MSSQL), bail
        # out early if no fixtures are found.
        for fixture_label in fixture_labels:
            if self.find_fixtures(fixture_label):
                break
        else:
            return

        self.objs_with_deferred_fields = []
        with connection.constraint_checks_disabled():
            for fixture_label in fixture_labels:
                self.load_label(fixture_label)
            for obj in self.objs_with_deferred_fields:
                obj.save_deferred_fields(using=self.using)

        # Since we disabled constraint checks, we must manually check for
        # any invalid keys that might have been added
        table_names = [model._meta.db_table for model in self.models]
        try:
            connection.check_constraints(table_names=table_names)
        except Exception as e:
            e.args = ("Problem installing fixtures: %s" % e,)
            raise

        # If we found even one object in a fixture, we need to reset the
        # database sequences.
        if self.loaded_object_count > 0:
            self.reset_sequences(connection, self.models)

        if self.verbosity >= 1:
            if self.fixture_object_count == self.loaded_object_count:
                self.stdout.write(
                    "Installed %d object(s) from %d fixture(s)"
                    % (self.loaded_object_count, self.fixture_count)
                )
            else:
                self.stdout.write(
                    "Installed %d object(s) (of %d) from %d fixture(s)"
                    % (
                        self.loaded_object_count,
                        self.fixture_object_count,
                        self.fixture_count,
                    )
                )

    def save_obj(self, obj):
        """Save an object if permitted."""
        if (
            obj.object._meta.app_config in self.excluded_apps
            or type(obj.object) in self.excluded_models
        ):
            return False
        saved = False
        if router.allow_migrate_model(self.using, obj.object.__class__):
            saved = True
            self.models.add(obj.object.__class__)
            try:
                obj.save(using=self.using)
            # psycopg raises ValueError if data contains NUL chars.
            except (DatabaseError, IntegrityError, ValueError) as e:
                e.args = (
                    "Could not load %(object_label)s(pk=%(pk)s): %(error_msg)s"
                    % {
                        "object_label": obj.object._meta.label,
                        "pk": obj.object.pk,
                        "error_msg": e,
                    },
                )
                raise
        if obj.deferred_fields:
            self.objs_with_deferred_fields.append(obj)
        return saved

    def load_label(self, fixture_label):
        """Load fixtures files for a given label."""
        show_progress = self.verbosity >= 3
        for fixture_file, fixture_dir, fixture_name in self.find_fixtures(
            fixture_label
        ):
            _, ser_fmt, cmp_fmt = self.parse_name(os.path.basename(fixture_file))
            open_method, mode = self.compression_formats[cmp_fmt]
            fixture = open_method(fixture_file, mode)
            self.fixture_count += 1
            objects_in_fixture = 0
            loaded_objects_in_fixture = 0
            if self.verbosity >= 2:
                self.stdout.write(
                    "Installing %s fixture '%s' from %s."
                    % (ser_fmt, fixture_name, humanize(fixture_dir))
                )
            try:
                objects = serializers.deserialize(
                    ser_fmt,
                    fixture,
                    using=self.using,
                    ignorenonexistent=self.ignore,
                    handle_forward_references=True,
                )

                for obj in objects:
                    objects_in_fixture += 1
                    if self.save_obj(obj):
                        loaded_objects_in_fixture += 1
                        if show_progress:
                            self.stdout.write(
                                "\rProcessed %i object(s)." % loaded_objects_in_fixture,
                                ending="",
                            )
            except Exception as e:
                if not isinstance(e, CommandError):
                    e.args = (
                        "Problem installing fixture '%s': %s" % (fixture_file, e),
                    )
                raise
            finally:
                fixture.close()

            if objects_in_fixture and show_progress:
                self.stdout.write()  # Add a newline after progress indicator.
            self.loaded_object_count += loaded_objects_in_fixture
            self.fixture_object_count += objects_in_fixture
            # Warn if the fixture we loaded contains 0 objects.
            if objects_in_fixture == 0:
                warnings.warn(
                    "No fixture data found for '%s'. (File format may be "
                    "invalid.)" % fixture_name,
                    RuntimeWarning,
                )

    def get_fixture_name_and_dirs(self, fixture_name):
        dirname, basename = os.path.split(fixture_name)
        if os.path.isabs(fixture_name):
            fixture_dirs = [dirname]
        else:
            fixture_dirs = self.fixture_dirs
            if os.path.sep in os.path.normpath(fixture_name):
                fixture_dirs = [os.path.join(dir_, dirname) for dir_ in fixture_dirs]
        return basename, fixture_dirs

    def get_targets(self, fixture_name, ser_fmt, cmp_fmt):
        databases = [self.using, None]
        cmp_fmts = self.compression_formats if cmp_fmt is None else [cmp_fmt]
        ser_fmts = self.serialization_formats if ser_fmt is None else [ser_fmt]
        return {
            "%s.%s"
            % (
                fixture_name,
                ".".join([ext for ext in combo if ext]),
            )
            for combo in product(databases, ser_fmts, cmp_fmts)
        }

    def find_fixture_files_in_dir(self, fixture_dir, fixture_name, targets):
        fixture_files_in_dir = []
        path = os.path.join(fixture_dir, fixture_name)
        for candidate in glob.iglob(glob.escape(path) + "*"):
            if os.path.basename(candidate) in targets:
                # Save the fixture_dir and fixture_name for future error
                # messages.
                fixture_files_in_dir.append((candidate, fixture_dir, fixture_name))
        return fixture_files_in_dir

    @functools.cache
    def find_fixtures(self, fixture_label):
        """Find fixture files for a given label."""
        if fixture_label == READ_STDIN:
            return [(READ_STDIN, None, READ_STDIN)]

        fixture_name, ser_fmt, cmp_fmt = self.parse_name(fixture_label)
        if self.verbosity >= 2:
            self.stdout.write("Loading '%s' fixtures..." % fixture_name)

        fixture_name, fixture_dirs = self.get_fixture_name_and_dirs(fixture_name)
        targets = self.get_targets(fixture_name, ser_fmt, cmp_fmt)
        fixture_files = []
        for fixture_dir in fixture_dirs:
            if self.verbosity >= 2:
                self.stdout.write("Checking %s for fixtures..." % humanize(fixture_dir))
            fixture_files_in_dir = self.find_fixture_files_in_dir(
                fixture_dir,
                fixture_name,
                targets,
            )
            if self.verbosity >= 2 and not fixture_files_in_dir:
                self.stdout.write(
                    "No fixture '%s' in %s." % (fixture_name, humanize(fixture_dir))
                )

            # Check kept for backwards-compatibility; it isn't clear why
            # duplicates are only allowed in different directories.
            if len(fixture_files_in_dir) > 1:
                raise CommandError(
                    "Multiple fixtures named '%s' in %s. Aborting."
                    % (fixture_name, humanize(fixture_dir))
                )
            fixture_files.extend(fixture_files_in_dir)

        if not fixture_files:
            raise CommandError("No fixture named '%s' found." % fixture_name)

        return fixture_files

    @cached_property
    def fixture_dirs(self):
        """
        Return a list of fixture directories.

        The list contains the 'fixtures' subdirectory of each installed
        application, if it exists, the directories in FIXTURE_DIRS, and the
        current directory.
        """
        dirs = []
        fixture_dirs = settings.FIXTURE_DIRS
        if len(fixture_dirs) != len(set(fixture_dirs)):
            raise ImproperlyConfigured("settings.FIXTURE_DIRS contains duplicates.")
        for app_config in apps.get_app_configs():
            app_label = app_config.label
            app_dir = os.path.join(app_config.path, "fixtures")
            if app_dir in [str(d) for d in fixture_dirs]:
                raise ImproperlyConfigured(
                    "'%s' is a default fixture directory for the '%s' app "
                    "and cannot be listed in settings.FIXTURE_DIRS."
                    % (app_dir, app_label)
                )

            if self.app_label and app_label != self.app_label:
                continue
            if os.path.isdir(app_dir):
                dirs.append(app_dir)
        dirs.extend(fixture_dirs)
        dirs.append("")
        return [os.path.realpath(d) for d in dirs]

    def parse_name(self, fixture_name):
        """
        Split fixture name in name, serialization format, compression format.
        """
        if fixture_name == READ_STDIN:
            if not self.format:
                raise CommandError(
                    "--format must be specified when reading from stdin."
                )
            return READ_STDIN, self.format, "stdin"

        parts = fixture_name.rsplit(".", 2)

        if len(parts) > 1 and parts[-1] in self.compression_formats:
            cmp_fmt = parts[-1]
            parts = parts[:-1]
        else:
            cmp_fmt = None

        if len(parts) > 1:
            if parts[-1] in self.serialization_formats:
                ser_fmt = parts[-1]
                parts = parts[:-1]
            else:
                raise CommandError(
                    "Problem installing fixture '%s': %s is not a known "
                    "serialization format." % (".".join(parts[:-1]), parts[-1])
                )
        else:
            ser_fmt = None

        name = ".".join(parts)

        return name, ser_fmt, cmp_fmt


class SingleZipReader(zipfile.ZipFile):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if len(self.namelist()) != 1:
            raise ValueError("Zip-compressed fixtures must contain one file.")

    def read(self):
        return zipfile.ZipFile.read(self, self.namelist()[0])


def humanize(dirname):
    return "'%s'" % dirname if dirname else "absolute path"
