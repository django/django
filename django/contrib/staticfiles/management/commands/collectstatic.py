from __future__ import unicode_literals

import os
from collections import OrderedDict

from django.apps import apps
from django.contrib.staticfiles.finders import get_finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
from django.utils.six.moves import input


class Command(BaseCommand):
    """
    Command that allows to copy or symlink static files from different
    locations to the settings.STATIC_ROOT.
    """
    help = "Collect static files in a single location."
    requires_system_checks = False

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.copied_files = []
        self.symlinked_files = []
        self.unmodified_files = []
        self.post_processed_files = []
        self.storage = staticfiles_storage
        self.style = no_style()

    @cached_property
    def local(self):
        try:
            self.storage.path('')
        except NotImplementedError:
            return False
        return True

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput', '--no-input',
            action='store_false', dest='interactive', default=True,
            help="Do NOT prompt the user for input of any kind.",
        )
        parser.add_argument(
            '--no-post-process',
            action='store_false', dest='post_process', default=True,
            help="Do NOT post process collected files.",
        )
        parser.add_argument(
            '-i', '--ignore', action='append', default=[],
            dest='ignore_patterns', metavar='PATTERN',
            help="Ignore files or directories matching this glob-style "
                 "pattern. Use multiple times to ignore more.",
        )
        parser.add_argument(
            '-n', '--dry-run',
            action='store_true', dest='dry_run', default=False,
            help="Do everything except modify the filesystem.",
        )
        parser.add_argument(
            '-c', '--clear',
            action='store_true', dest='clear', default=False,
            help="Clear the existing files using the storage "
                 "before trying to copy or link the original file.",
        )
        parser.add_argument(
            '-l', '--link',
            action='store_true', dest='link', default=False,
            help="Create a symbolic link to each file instead of copying.",
        )
        parser.add_argument(
            '--no-default-ignore', action='store_false',
            dest='use_default_ignore_patterns', default=True,
            help="Don't ignore the common private glob-style patterns (defaults to 'CVS', '.*' and '*~').",
        )

    def set_options(self, **options):
        """
        Set instance variables based on an options dict
        """
        self.interactive = options['interactive']
        self.verbosity = options['verbosity']
        self.symlink = options['link']
        self.clear = options['clear']
        self.dry_run = options['dry_run']
        ignore_patterns = options['ignore_patterns']
        if options['use_default_ignore_patterns']:
            ignore_patterns += apps.get_app_config('staticfiles').ignore_patterns
        self.ignore_patterns = list(set(ignore_patterns))
        self.post_process = options['post_process']

    def collect(self):
        """
        Perform the bulk of the work of collectstatic.

        Split off from handle() to facilitate testing.
        """
        if self.symlink and not self.local:
            raise CommandError("Can't symlink to a remote destination.")

        if self.clear:
            self.clear_dir('')

        if self.symlink:
            handler = self.link_file
        else:
            handler = self.copy_file

        found_files = OrderedDict()
        for finder in get_finders():
            for path, storage in finder.list(self.ignore_patterns):
                # Prefix the relative path if the source storage contains it
                if getattr(storage, 'prefix', None):
                    prefixed_path = os.path.join(storage.prefix, path)
                else:
                    prefixed_path = path

                if prefixed_path not in found_files:
                    found_files[prefixed_path] = (storage, path)
                    handler(path, prefixed_path, storage)
                else:
                    self.log(
                        "Found another file with the destination path '%s'. It "
                        "will be ignored since only the first encountered file "
                        "is collected. If this is not what you want, make sure "
                        "every static file has a unique path." % prefixed_path,
                        level=1,
                    )

        # Here we check if the storage backend has a post_process
        # method and pass it the list of modified files.
        if self.post_process and hasattr(self.storage, 'post_process'):
            processor = self.storage.post_process(found_files,
                                                  dry_run=self.dry_run)
            for original_path, processed_path, processed in processor:
                if isinstance(processed, Exception):
                    self.stderr.write("Post-processing '%s' failed!" % original_path)
                    # Add a blank line before the traceback, otherwise it's
                    # too easy to miss the relevant part of the error message.
                    self.stderr.write("")
                    raise processed
                if processed:
                    self.log("Post-processed '%s' as '%s'" %
                             (original_path, processed_path), level=1)
                    self.post_processed_files.append(original_path)
                else:
                    self.log("Skipped post-processing '%s'" % original_path)

        return {
            'modified': self.copied_files + self.symlinked_files,
            'unmodified': self.unmodified_files,
            'post_processed': self.post_processed_files,
        }

    def handle(self, **options):
        self.set_options(**options)

        message = ['\n']
        if self.dry_run:
            message.append(
                'You have activated the --dry-run option so no files will be modified.\n\n'
            )

        message.append(
            'You have requested to collect static files at the destination\n'
            'location as specified in your settings'
        )

        if self.is_local_storage() and self.storage.location:
            destination_path = self.storage.location
            message.append(':\n\n    %s\n\n' % destination_path)
        else:
            destination_path = None
            message.append('.\n\n')

        if self.clear:
            message.append('This will DELETE ALL FILES in this location!\n')
        else:
            message.append('This will overwrite existing files!\n')

        message.append(
            'Are you sure you want to do this?\n\n'
            "Type 'yes' to continue, or 'no' to cancel: "
        )

        if self.interactive and input(''.join(message)) != 'yes':
            raise CommandError("Collecting static files cancelled.")

        collected = self.collect()
        modified_count = len(collected['modified'])
        unmodified_count = len(collected['unmodified'])
        post_processed_count = len(collected['post_processed'])

        if self.verbosity >= 1:
            template = ("\n%(modified_count)s %(identifier)s %(action)s"
                        "%(destination)s%(unmodified)s%(post_processed)s.\n")
            summary = template % {
                'modified_count': modified_count,
                'identifier': 'static file' + ('' if modified_count == 1 else 's'),
                'action': 'symlinked' if self.symlink else 'copied',
                'destination': (" to '%s'" % destination_path if destination_path else ''),
                'unmodified': (', %s unmodified' % unmodified_count if collected['unmodified'] else ''),
                'post_processed': (collected['post_processed'] and
                                   ', %s post-processed'
                                   % post_processed_count or ''),
            }
            return summary

    def log(self, msg, level=2):
        """
        Small log helper
        """
        if self.verbosity >= level:
            self.stdout.write(msg)

    def is_local_storage(self):
        return isinstance(self.storage, FileSystemStorage)

    def clear_dir(self, path):
        """
        Deletes the given relative path using the destination storage backend.
        """
        if not self.storage.exists(path):
            return

        dirs, files = self.storage.listdir(path)
        for f in files:
            fpath = os.path.join(path, f)
            if self.dry_run:
                self.log("Pretending to delete '%s'" %
                         smart_text(fpath), level=1)
            else:
                self.log("Deleting '%s'" % smart_text(fpath), level=1)
                try:
                    full_path = self.storage.path(fpath)
                except NotImplementedError:
                    self.storage.delete(fpath)
                else:
                    if not os.path.exists(full_path) and os.path.lexists(full_path):
                        # Delete broken symlinks
                        os.unlink(full_path)
                    else:
                        self.storage.delete(fpath)
        for d in dirs:
            self.clear_dir(os.path.join(path, d))

    def delete_file(self, path, prefixed_path, source_storage):
        """
        Checks if the target file should be deleted if it already exists
        """
        if self.storage.exists(prefixed_path):
            try:
                # When was the target file modified last time?
                target_last_modified = self.storage.get_modified_time(prefixed_path)
            except (OSError, NotImplementedError, AttributeError):
                # The storage doesn't support get_modified_time() or failed
                pass
            else:
                try:
                    # When was the source file modified last time?
                    source_last_modified = source_storage.get_modified_time(path)
                except (OSError, NotImplementedError, AttributeError):
                    pass
                else:
                    # The full path of the target file
                    if self.local:
                        full_path = self.storage.path(prefixed_path)
                    else:
                        full_path = None
                    # Skip the file if the source file is younger
                    # Avoid sub-second precision (see #14665, #19540)
                    if (target_last_modified.replace(microsecond=0) >= source_last_modified.replace(microsecond=0) and
                            full_path and not (self.symlink ^ os.path.islink(full_path))):
                        if prefixed_path not in self.unmodified_files:
                            self.unmodified_files.append(prefixed_path)
                        self.log("Skipping '%s' (not modified)" % path)
                        return False
            # Then delete the existing file if really needed
            if self.dry_run:
                self.log("Pretending to delete '%s'" % path)
            else:
                self.log("Deleting '%s'" % path)
                self.storage.delete(prefixed_path)
        return True

    def link_file(self, path, prefixed_path, source_storage):
        """
        Attempt to link ``path``
        """
        # Skip this file if it was already copied earlier
        if prefixed_path in self.symlinked_files:
            return self.log("Skipping '%s' (already linked earlier)" % path)
        # Delete the target file if needed or break
        if not self.delete_file(path, prefixed_path, source_storage):
            return
        # The full path of the source file
        source_path = source_storage.path(path)
        # Finally link the file
        if self.dry_run:
            self.log("Pretending to link '%s'" % source_path, level=1)
        else:
            self.log("Linking '%s'" % source_path, level=1)
            full_path = self.storage.path(prefixed_path)
            try:
                os.makedirs(os.path.dirname(full_path))
            except OSError:
                pass
            try:
                if os.path.lexists(full_path):
                    os.unlink(full_path)
                os.symlink(source_path, full_path)
            except AttributeError:
                import platform
                raise CommandError("Symlinking is not supported by Python %s." %
                                   platform.python_version())
            except NotImplementedError:
                import platform
                raise CommandError("Symlinking is not supported in this "
                                   "platform (%s)." % platform.platform())
            except OSError as e:
                raise CommandError(e)
        if prefixed_path not in self.symlinked_files:
            self.symlinked_files.append(prefixed_path)

    def copy_file(self, path, prefixed_path, source_storage):
        """
        Attempt to copy ``path`` with storage
        """
        # Skip this file if it was already copied earlier
        if prefixed_path in self.copied_files:
            return self.log("Skipping '%s' (already copied earlier)" % path)
        # Delete the target file if needed or break
        if not self.delete_file(path, prefixed_path, source_storage):
            return
        # The full path of the source file
        source_path = source_storage.path(path)
        # Finally start copying
        if self.dry_run:
            self.log("Pretending to copy '%s'" % source_path, level=1)
        else:
            self.log("Copying '%s'" % source_path, level=1)
            with source_storage.open(path) as source_file:
                self.storage.save(prefixed_path, source_file)
        self.copied_files.append(prefixed_path)
