import codecs
import concurrent.futures
import glob
import os
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.management.utils import find_command, is_ignored_path, popen_wrapper


def has_bom(fn):
    with fn.open("rb") as f:
        sample = f.read(4)
    return sample.startswith(
        (codecs.BOM_UTF8, codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)
    )


def is_dir_writable(path):
    try:
        with tempfile.NamedTemporaryFile(dir=path):
            pass
    except OSError:
        return False
    return True


class Command(BaseCommand):
    help = "Compiles .po files to .mo files for use with builtin gettext support."

    requires_system_checks = []

    program = "msgfmt"
    program_options = ["--check-format"]

    def add_arguments(self, parser):
        parser.add_argument(
            "--locale",
            "-l",
            action="append",
            default=[],
            help="Locale(s) to process (e.g. de_AT). Default is to process all. "
            "Can be used multiple times.",
        )
        parser.add_argument(
            "--exclude",
            "-x",
            action="append",
            default=[],
            help="Locales to exclude. Default is none. Can be used multiple times.",
        )
        parser.add_argument(
            "--use-fuzzy",
            "-f",
            dest="fuzzy",
            action="store_true",
            help="Use fuzzy translations.",
        )
        parser.add_argument(
            "--ignore",
            "-i",
            action="append",
            dest="ignore_patterns",
            default=[],
            metavar="PATTERN",
            help="Ignore directories matching this glob-style pattern. "
            "Use multiple times to ignore more.",
        )

    def handle(self, **options):
        locale = options["locale"]
        exclude = options["exclude"]
        ignore_patterns = set(options["ignore_patterns"])
        self.verbosity = options["verbosity"]
        if options["fuzzy"]:
            self.program_options = self.program_options + ["-f"]

        if find_command(self.program) is None:
            raise CommandError(
                f"Can't find {self.program}. Make sure you have GNU gettext "
                "tools 0.19 or newer installed."
            )

        basedirs = [os.path.join("conf", "locale"), "locale"]
        if os.environ.get("DJANGO_SETTINGS_MODULE"):
            from django.conf import settings

            basedirs.extend(settings.LOCALE_PATHS)

        # Walk entire tree, looking for locale directories
        for dirpath, dirnames, filenames in os.walk(".", topdown=True):
            # As we may modify dirnames, iterate through a copy of it instead
            for dirname in list(dirnames):
                if is_ignored_path(
                    os.path.normpath(os.path.join(dirpath, dirname)), ignore_patterns
                ):
                    dirnames.remove(dirname)
                elif dirname == "locale":
                    basedirs.append(os.path.join(dirpath, dirname))

        # Gather existing directories.
        basedirs = set(map(os.path.abspath, filter(os.path.isdir, basedirs)))

        if not basedirs:
            raise CommandError(
                "This script should be run from the Django Git "
                "checkout or your project or app tree, or with "
                "the settings module specified."
            )

        # Build locale list
        all_locales = []
        for basedir in basedirs:
            locale_dirs = filter(os.path.isdir, glob.glob("%s/*" % basedir))
            all_locales.extend(map(os.path.basename, locale_dirs))

        # Account for excluded locales
        locales = locale or all_locales
        locales = set(locales).difference(exclude)

        self.has_errors = False
        for basedir in basedirs:
            if locales:
                dirs = [
                    os.path.join(basedir, locale, "LC_MESSAGES") for locale in locales
                ]
            else:
                dirs = [basedir]
            locations = []
            for ldir in dirs:
                for dirpath, dirnames, filenames in os.walk(ldir):
                    locations.extend(
                        (dirpath, f) for f in filenames if f.endswith(".po")
                    )
            if locations:
                self.compile_messages(locations)

        if self.has_errors:
            raise CommandError("compilemessages generated one or more errors.")

    def compile_messages(self, locations):
        """
        Locations is a list of tuples: [(directory, file), ...]
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for i, (dirpath, f) in enumerate(locations):
                po_path = Path(dirpath) / f
                mo_path = po_path.with_suffix(".mo")
                try:
                    if mo_path.stat().st_mtime >= po_path.stat().st_mtime:
                        if self.verbosity > 0:
                            self.stdout.write(
                                "File “%s” is already compiled and up to date."
                                % po_path
                            )
                        continue
                except FileNotFoundError:
                    pass
                if self.verbosity > 0:
                    self.stdout.write("processing file %s in %s" % (f, dirpath))

                if has_bom(po_path):
                    self.stderr.write(
                        "The %s file has a BOM (Byte Order Mark). Django only "
                        "supports .po files encoded in UTF-8 and without any BOM."
                        % po_path
                    )
                    self.has_errors = True
                    continue

                # Check writability on first location
                if i == 0 and not is_dir_writable(mo_path.parent):
                    self.stderr.write(
                        "The po files under %s are in a seemingly not writable "
                        "location. mo files will not be updated/created." % dirpath
                    )
                    self.has_errors = True
                    return

                args = [self.program, *self.program_options, "-o", mo_path, po_path]
                futures.append(executor.submit(popen_wrapper, args))

            for future in concurrent.futures.as_completed(futures):
                output, errors, status = future.result()
                if status:
                    if self.verbosity > 0:
                        if errors:
                            self.stderr.write(
                                "Execution of %s failed: %s" % (self.program, errors)
                            )
                        else:
                            self.stderr.write("Execution of %s failed" % self.program)
                    self.has_errors = True
