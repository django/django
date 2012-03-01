import os
import sys
import shutil
from optparse import make_option

from django.conf import settings
from django.core.files.storage import get_storage_class
from django.core.management.base import CommandError, NoArgsCommand
from django.utils.encoding import smart_str

from django.contrib.staticfiles import finders

class Command(NoArgsCommand):
    """
    Command that allows to copy or symlink media files from different
    locations to the settings.STATIC_ROOT.
    """
    option_list = NoArgsCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive',
            default=True, help="Do NOT prompt the user for input of any kind."),
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

    def __init__(self, *args, **kwargs):
        super(NoArgsCommand, self).__init__(*args, **kwargs)
        self.copied_files = []
        self.symlinked_files = []
        self.unmodified_files = []
        self.storage = get_storage_class(settings.STATICFILES_STORAGE)()
        try:
            self.storage.path('')
        except NotImplementedError:
            self.local = False
        else:
            self.local = True
        # Use ints for file times (ticket #14665)
        os.stat_float_times(False)

    def handle_noargs(self, **options):
        symlink = options['link']
        ignore_patterns = options['ignore_patterns']
        if options['use_default_ignore_patterns']:
            ignore_patterns += ['CVS', '.*', '*~']
        ignore_patterns = list(set(ignore_patterns))
        self.verbosity = int(options.get('verbosity', 1))

        if symlink:
            if sys.platform == 'win32':
                raise CommandError("Symlinking is not supported by this "
                                   "platform (%s)." % sys.platform)
            if not self.local:
                raise CommandError("Can't symlink to a remote destination.")

        # Warn before doing anything more.
        if options.get('interactive'):
            confirm = raw_input(u"""
You have requested to collect static files at the destination
location as specified in your settings file.

This will overwrite existing files.
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """)
            if confirm != 'yes':
                raise CommandError("Collecting static files cancelled.")

        processed_files = []
        for finder in finders.get_finders():
            for path, storage in finder.list(ignore_patterns):
                # Prefix the relative path if the source storage contains it
                if getattr(storage, 'prefix', None):
                    prefixed_path = os.path.join(storage.prefix, path)
                else:
                    prefixed_path = path
                if prefixed_path in processed_files:
                    continue
                if symlink:
                    self.link_file(path, prefixed_path, storage, **options)
                else:
                    self.copy_file(path, prefixed_path, storage, **options)
                processed_files.append(prefixed_path)

        actual_count = len(self.copied_files) + len(self.symlinked_files)
        unmodified_count = len(self.unmodified_files)
        if self.verbosity >= 1:
            self.stdout.write(smart_str(u"\n%s static file%s %s to '%s'%s.\n"
                              % (actual_count, actual_count != 1 and 's' or '',
                                 symlink and 'symlinked' or 'copied',
                                 settings.STATIC_ROOT,
                                 unmodified_count and ' (%s unmodified)'
                                 % unmodified_count or '')))

    def log(self, msg, level=2):
        """
        Small log helper
        """
        msg = smart_str(msg)
        if not msg.endswith("\n"):
            msg += "\n"
        if self.verbosity >= level:
            self.stdout.write(msg)

    def delete_file(self, path, prefixed_path, source_storage, **options):
        # Whether we are in symlink mode
        symlink = options['link']
        # Checks if the target file should be deleted if it already exists
        if self.storage.exists(prefixed_path):
            try:
                # When was the target file modified last time?
                target_last_modified = self.storage.modified_time(prefixed_path)
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
                        if not ((symlink and full_path and not os.path.islink(full_path)) or
                                (not symlink and full_path and os.path.islink(full_path))):
                            if prefixed_path not in self.unmodified_files:
                                self.unmodified_files.append(prefixed_path)
                            self.log(u"Skipping '%s' (not modified)" % path)
                            return False
            # Then delete the existing file if really needed
            if options['dry_run']:
                self.log(u"Pretending to delete '%s'" % path)
            else:
                self.log(u"Deleting '%s'" % path)
                self.storage.delete(prefixed_path)
        return True

    def link_file(self, path, prefixed_path, source_storage, **options):
        """
        Attempt to link ``path``
        """
        # Skip this file if it was already copied earlier
        if prefixed_path in self.symlinked_files:
            return self.log(u"Skipping '%s' (already linked earlier)" % path)
        # Delete the target file if needed or break
        if not self.delete_file(path, prefixed_path, source_storage, **options):
            return
        # The full path of the source file
        source_path = source_storage.path(path)
        # Finally link the file
        if options['dry_run']:
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

    def copy_file(self, path, prefixed_path, source_storage, **options):
        """
        Attempt to copy ``path`` with storage
        """
        # Skip this file if it was already copied earlier
        if prefixed_path in self.copied_files:
            return self.log(u"Skipping '%s' (already copied earlier)" % path)
        # Delete the target file if needed or break
        if not self.delete_file(path, prefixed_path, source_storage, **options):
            return
        # The full path of the source file
        source_path = source_storage.path(path)
        # Finally start copying
        if options['dry_run']:
            self.log(u"Pretending to copy '%s'" % source_path, level=1)
        else:
            self.log(u"Copying '%s'" % source_path, level=1)
            if self.local:
                full_path = self.storage.path(prefixed_path)
                try:
                    os.makedirs(os.path.dirname(full_path))
                except OSError:
                    pass
            source_file = source_storage.open(path)
            self.storage.save(prefixed_path, source_file)
        if not prefixed_path in self.copied_files:
            self.copied_files.append(prefixed_path)
