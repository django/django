import os
import sys
import shutil
from optparse import make_option

from django.conf import settings
from django.core.files.storage import get_storage_class
from django.core.management.base import CommandError, NoArgsCommand

from django.contrib.staticfiles import finders

class Command(NoArgsCommand):
    """
    Command that allows to copy or symlink media files from different
    locations to the settings.STATICFILES_ROOT.
    """
    option_list = NoArgsCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive',
            default=True, help="Do NOT prompt the user for input of any "
                "kind."),
        make_option('-i', '--ignore', action='append', default=[],
            dest='ignore_patterns', metavar='PATTERN',
            help="Ignore files or directories matching this glob-style "
                "pattern. Use multiple times to ignore more."),
        make_option('-n', '--dry-run', action='store_true', dest='dry_run',
            default=False, help="Do everything except modify the filesystem."),
        make_option('-l', '--link', action='store_true', dest='link',
            default=False, help="Create a symbolic link to each file instead of copying."),
        make_option('--no-default-ignore', action='store_false',
            dest='use_default_ignore_patterns', default=True,
            help="Don't ignore the common private glob-style patterns 'CVS', "
                "'.*' and '*~'."),
    )
    help = "Collect static files from apps and other locations in a single location."

    def handle_noargs(self, **options):
        symlink = options['link']
        ignore_patterns = options['ignore_patterns']
        if options['use_default_ignore_patterns']:
            ignore_patterns += ['CVS', '.*', '*~']
        ignore_patterns = list(set(ignore_patterns))
        self.copied_files = set()
        self.symlinked_files = set()
        self.unmodified_files = set()
        self.destination_storage = get_storage_class(settings.STATICFILES_STORAGE)()

        try:
            self.destination_storage.path('')
        except NotImplementedError:
            self.destination_local = False
        else:
            self.destination_local = True

        if symlink:
            if sys.platform == 'win32':
                raise CommandError("Symlinking is not supported by this "
                                   "platform (%s)." % sys.platform)
            if not self.destination_local:
                raise CommandError("Can't symlink to a remote destination.")

        # Warn before doing anything more.
        if options.get('interactive'):
            confirm = raw_input("""
You have requested to collate static files and collect them at the destination
location as specified in your settings file.

This will overwrite existing files.
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """)
            if confirm != 'yes':
                raise CommandError("Static files build cancelled.")

        for finder in finders.get_finders():
            for source, prefix, storage in finder.list(ignore_patterns):
                self.copy_file(source, prefix, storage, **options)

        verbosity = int(options.get('verbosity', 1))
        actual_count = len(self.copied_files) + len(self.symlinked_files)
        unmodified_count = len(self.unmodified_files)
        if verbosity >= 1:
            self.stdout.write("\n%s static file%s %s to '%s'%s.\n"
                              % (actual_count, actual_count != 1 and 's' or '',
                                 symlink and 'symlinked' or 'copied',
                                 settings.STATICFILES_ROOT,
                                 unmodified_count and ' (%s unmodified)'
                                 % unmodified_count or ''))

    def copy_file(self, source, prefix, source_storage, **options):
        """
        Attempt to copy (or symlink) ``source`` to ``destination``,
        returning True if successful.
        """
        source_path = source_storage.path(source)
        try:
            source_last_modified = source_storage.modified_time(source)
        except (OSError, NotImplementedError):
            source_last_modified = None
        if prefix:
            destination = '/'.join([prefix, source])
        else:
            destination = source
        symlink = options['link']
        dry_run = options['dry_run']
        verbosity = int(options.get('verbosity', 1))

        if destination in self.copied_files:
            if verbosity >= 2:
                self.stdout.write("Skipping '%s' (already copied earlier)\n"
                                  % destination)
            return False

        if destination in self.symlinked_files:
            if verbosity >= 2:
                self.stdout.write("Skipping '%s' (already linked earlier)\n"
                                  % destination)
            return False

        if self.destination_storage.exists(destination):
            try:
                destination_last_modified = \
                    self.destination_storage.modified_time(destination)
            except (OSError, NotImplementedError):
                # storage doesn't support ``modified_time`` or failed.
                pass
            else:
                destination_is_link = os.path.islink(
                    self.destination_storage.path(destination))
                if destination_last_modified == source_last_modified:
                    if (not symlink and not destination_is_link):
                        if verbosity >= 2:
                            self.stdout.write("Skipping '%s' (not modified)\n"
                                              % destination)
                        self.unmodified_files.add(destination)
                        return False
            if dry_run:
                if verbosity >= 2:
                    self.stdout.write("Pretending to delete '%s'\n"
                                      % destination)
            else:
                if verbosity >= 2:
                    self.stdout.write("Deleting '%s'\n" % destination)
                self.destination_storage.delete(destination)

        if symlink:
            destination_path = self.destination_storage.path(destination)
            if dry_run:
                if verbosity >= 1:
                    self.stdout.write("Pretending to symlink '%s' to '%s'\n"
                                      % (source_path, destination_path))
            else:
                if verbosity >= 1:
                    self.stdout.write("Symlinking '%s' to '%s'\n"
                                      % (source_path, destination_path))
                try:
                    os.makedirs(os.path.dirname(destination_path))
                except OSError:
                    pass
                os.symlink(source_path, destination_path)
            self.symlinked_files.add(destination)
        else:
            if dry_run:
                if verbosity >= 1:
                    self.stdout.write("Pretending to copy '%s' to '%s'\n"
                                      % (source_path, destination))
            else:
                if self.destination_local:
                    destination_path = self.destination_storage.path(destination)
                    try:
                        os.makedirs(os.path.dirname(destination_path))
                    except OSError:
                        pass
                    shutil.copy2(source_path, destination_path)
                    if verbosity >= 1:
                        self.stdout.write("Copying '%s' to '%s'\n"
                                          % (source_path, destination_path))
                else:
                    source_file = source_storage.open(source)
                    self.destination_storage.save(destination, source_file)
                    if verbosity >= 1:
                        self.stdout.write("Copying %s to %s\n"
                                          % (source_path, destination))
            self.copied_files.add(destination)
        return True
