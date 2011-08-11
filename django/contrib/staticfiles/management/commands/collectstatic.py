from __future__ import with_statement

import os
import sys
from optparse import make_option

from django.core.files.storage import FileSystemStorage
from django.core.management.base import CommandError, NoArgsCommand
from django.utils.encoding import smart_str, smart_unicode

from django.contrib.staticfiles import finders, storage


class Command(NoArgsCommand):
    """
    Command that allows to copy or symlink media files from different
    locations to the settings.STATIC_ROOT.
    """
    option_list = NoArgsCommand.option_list + (
        make_option('--noinput',
            action='store_false', dest='interactive', default=True,
            help="Do NOT prompt the user for input of any kind."),
        make_option('--no-post-process',
            action='store_false', dest='post_process', default=True,
            help="Do NOT post process collected files."),
        make_option('-i', '--ignore', action='append', default=[],
            dest='ignore_patterns', metavar='PATTERN',
            help="Ignore files or directories matching this glob-style "
                "pattern. Use multiple times to ignore more."),
        make_option('-n', '--dry-run',
            action='store_true', dest='dry_run', default=False,
            help="Do everything except modify the filesystem."),
        make_option('-c', '--clear',
            action='store_true', dest='clear', default=False,
            help="Clear the existing files using the storage "
                 "before trying to copy or link the original file."),
        make_option('-l', '--link',
            action='store_true', dest='link', default=False,
            help="Create a symbolic link to each file instead of copying."),
        make_option('--no-default-ignore', action='store_false',
            dest='use_default_ignore_patterns', default=True,
            help="Don't ignore the common private glob-style patterns 'CVS', "
                "'.*' and '*~'."),
    )
    help = "Collect static files in a single location."

    def __init__(self, *args, **kwargs):
        super(NoArgsCommand, self).__init__(*args, **kwargs)
        self.copied_files = []
        self.symlinked_files = []
        self.unmodified_files = []
        self.storage = storage.staticfiles_storage
        try:
            self.storage.path('')
        except NotImplementedError:
            self.local = False
        else:
            self.local = True
        # Use ints for file times (ticket #14665), if supported
        if hasattr(os, 'stat_float_times'):
            os.stat_float_times(False)

    def handle_noargs(self, **options):
        self.clear = options['clear']
        self.dry_run = options['dry_run']
        ignore_patterns = options['ignore_patterns']
        if options['use_default_ignore_patterns']:
            ignore_patterns += ['CVS', '.*', '*~']
        self.ignore_patterns = list(set(ignore_patterns))
        self.interactive = options['interactive']
        self.symlink = options['link']
        self.verbosity = int(options.get('verbosity', 1))
        self.post_process = options['post_process']

        if self.symlink:
            if sys.platform == 'win32':
                raise CommandError("Symlinking is not supported by this "
                                   "platform (%s)." % sys.platform)
            if not self.local:
                raise CommandError("Can't symlink to a remote destination.")

        # Warn before doing anything more.
        if (isinstance(self.storage, FileSystemStorage) and
                self.storage.location):
            destination_path = self.storage.location
            destination_display = ':\n\n    %s' % destination_path
        else:
            destination_path = None
            destination_display = '.'

        if self.clear:
            clear_display = 'This will DELETE EXISTING FILES!'
        else:
            clear_display = 'This will overwrite existing files!'

        if self.interactive:
            confirm = raw_input(u"""
You have requested to collect static files at the destination
location as specified in your settings%s

%s
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """
% (destination_display, clear_display))
            if confirm != 'yes':
                raise CommandError("Collecting static files cancelled.")

        if self.clear:
            self.clear_dir('')

        handler = {
            True: self.link_file,
            False: self.copy_file,
        }[self.symlink]

        found_files = []
        for finder in finders.get_finders():
            for path, storage in finder.list(self.ignore_patterns):
                # Prefix the relative path if the source storage contains it
                if getattr(storage, 'prefix', None):
                    prefixed_path = os.path.join(storage.prefix, path)
                else:
                    prefixed_path = path
                found_files.append(prefixed_path)
                handler(path, prefixed_path, storage)

        # Here we check if the storage backend has a post_process
        # method and pass it the list of modified files.
        if self.post_process and hasattr(self.storage, 'post_process'):
            post_processed = self.storage.post_process(found_files, **options)
            for path in post_processed:
                self.log(u"Post-processed '%s'" % path, level=1)
        else:
            post_processed = []

        modified_files = self.copied_files + self.symlinked_files
        actual_count = len(modified_files)
        unmodified_count = len(self.unmodified_files)

        if self.verbosity >= 1:
            template = ("\n%(actual_count)s %(identifier)s %(action)s"
                        "%(destination)s%(unmodified)s.\n")
            summary = template % {
                'actual_count': actual_count,
                'identifier': 'static file' + (actual_count > 1 and 's' or ''),
                'action': self.symlink and 'symlinked' or 'copied',
                'destination': (destination_path and " to '%s'"
                                % destination_path or ''),
                'unmodified': (self.unmodified_files and ', %s unmodified'
                               % unmodified_count or ''),
            }
            self.stdout.write(smart_str(summary))

    def log(self, msg, level=2):
        """
        Small log helper
        """
        msg = smart_str(msg)
        if not msg.endswith("\n"):
            msg += "\n"
        if self.verbosity >= level:
            self.stdout.write(msg)

    def clear_dir(self, path):
        """
        Deletes the given relative path using the destinatin storage backend.
        """
        dirs, files = self.storage.listdir(path)
        for f in files:
            fpath = os.path.join(path, f)
            if self.dry_run:
                self.log(u"Pretending to delete '%s'" %
                         smart_unicode(fpath), level=1)
            else:
                self.log(u"Deleting '%s'" % smart_unicode(fpath), level=1)
                self.storage.delete(fpath)
        for d in dirs:
            self.clear_dir(os.path.join(path, d))

    def delete_file(self, path, prefixed_path, source_storage):
        # Whether we are in symlink mode
        # Checks if the target file should be deleted if it already exists
        if self.storage.exists(prefixed_path):
            try:
                # When was the target file modified last time?
                target_last_modified = \
                    self.storage.modified_time(prefixed_path)
            except (OSError, NotImplementedError):
                # The storage doesn't support ``modified_time`` or failed
                pass
            else:
                try:
                    # When was the source file modified last time?
                    source_last_modified = source_storage.modified_time(path)
                except (OSError, NotImplementedError):
                    pass
                else:
                    # The full path of the target file
                    if self.local:
                        full_path = self.storage.path(prefixed_path)
                    else:
                        full_path = None
                    # Skip the file if the source file is younger
                    if target_last_modified >= source_last_modified:
                        if not ((self.symlink and full_path
                                 and not os.path.islink(full_path)) or
                                (not self.symlink and full_path
                                 and os.path.islink(full_path))):
                            if prefixed_path not in self.unmodified_files:
                                self.unmodified_files.append(prefixed_path)
                            self.log(u"Skipping '%s' (not modified)" % path)
                            return False
            # Then delete the existing file if really needed
            if self.dry_run:
                self.log(u"Pretending to delete '%s'" % path)
            else:
                self.log(u"Deleting '%s'" % path)
                self.storage.delete(prefixed_path)
        return True

    def link_file(self, path, prefixed_path, source_storage):
        """
        Attempt to link ``path``
        """
        # Skip this file if it was already copied earlier
        if prefixed_path in self.symlinked_files:
            return self.log(u"Skipping '%s' (already linked earlier)" % path)
        # Delete the target file if needed or break
        if not self.delete_file(path, prefixed_path, source_storage):
            return
        # The full path of the source file
        source_path = source_storage.path(path)
        # Finally link the file
        if self.dry_run:
            self.log(u"Pretending to link '%s'" % source_path, level=1)
        else:
            self.log(u"Linking '%s'" % source_path, level=1)
            full_path = self.storage.path(prefixed_path)
            try:
                os.makedirs(os.path.dirname(full_path))
            except OSError:
                pass
            os.symlink(source_path, full_path)
        if prefixed_path not in self.symlinked_files:
            self.symlinked_files.append(prefixed_path)

    def copy_file(self, path, prefixed_path, source_storage):
        """
        Attempt to copy ``path`` with storage
        """
        # Skip this file if it was already copied earlier
        if prefixed_path in self.copied_files:
            return self.log(u"Skipping '%s' (already copied earlier)" % path)
        # Delete the target file if needed or break
        if not self.delete_file(path, prefixed_path, source_storage):
            return
        # The full path of the source file
        source_path = source_storage.path(path)
        # Finally start copying
        if self.dry_run:
            self.log(u"Pretending to copy '%s'" % source_path, level=1)
        else:
            self.log(u"Copying '%s'" % source_path, level=1)
            if self.local:
                full_path = self.storage.path(prefixed_path)
                try:
                    os.makedirs(os.path.dirname(full_path))
                except OSError:
                    pass
            with source_storage.open(path) as source_file:
                self.storage.save(prefixed_path, source_file)
        if not prefixed_path in self.copied_files:
            self.copied_files.append(prefixed_path)
