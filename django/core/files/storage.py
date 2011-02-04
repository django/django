import os
import errno
import urlparse
import itertools
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.core.files import locks, File
from django.core.files.move import file_move_safe
from django.utils.encoding import force_unicode, filepath_to_uri
from django.utils.functional import LazyObject
from django.utils.importlib import import_module
from django.utils.text import get_valid_filename
from django.utils._os import safe_join

__all__ = ('Storage', 'FileSystemStorage', 'DefaultStorage', 'default_storage')

class Storage(object):
    """
    A base storage class, providing some default behaviors that all other
    storage systems can inherit or override, as necessary.
    """

    # The following methods represent a public interface to private methods.
    # These shouldn't be overridden by subclasses unless absolutely necessary.

    def open(self, name, mode='rb', mixin=None):
        """
        Retrieves the specified file from storage, using the optional mixin
        class to customize what features are available on the File returned.
        """
        file = self._open(name, mode)
        if mixin:
            # Add the mixin as a parent class of the File returned from storage.
            file.__class__ = type(mixin.__name__, (mixin, file.__class__), {})
        return file

    def save(self, name, content):
        """
        Saves new content to the file specified by name. The content should be a
        proper File object, ready to be read from the beginning.
        """
        # Get the proper name for the file, as it will actually be saved.
        if name is None:
            name = content.name

        name = self.get_available_name(name)
        name = self._save(name, content)

        # Store filenames with forward slashes, even on Windows
        return force_unicode(name.replace('\\', '/'))

    # These methods are part of the public API, with default implementations.

    def get_valid_name(self, name):
        """
        Returns a filename, based on the provided filename, that's suitable for
        use in the target storage system.
        """
        return get_valid_filename(name)

    def get_available_name(self, name):
        """
        Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        """
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        # If the filename already exists, add an underscore and a number (before
        # the file extension, if one exists) to the filename until the generated
        # filename doesn't exist.
        count = itertools.count(1)
        while self.exists(name):
            # file_ext includes the dot.
            name = os.path.join(dir_name, "%s_%s%s" % (file_root, count.next(), file_ext))

        return name

    def path(self, name):
        """
        Returns a local filesystem path where the file can be retrieved using
        Python's built-in open() function. Storage systems that can't be
        accessed using open() should *not* implement this method.
        """
        raise NotImplementedError("This backend doesn't support absolute paths.")

    # The following methods form the public API for storage systems, but with
    # no default implementations. Subclasses must implement *all* of these.

    def delete(self, name):
        """
        Deletes the specified file from the storage system.
        """
        raise NotImplementedError()

    def exists(self, name):
        """
        Returns True if a file referened by the given name already exists in the
        storage system, or False if the name is available for a new file.
        """
        raise NotImplementedError()

    def listdir(self, path):
        """
        Lists the contents of the specified path, returning a 2-tuple of lists;
        the first item being directories, the second item being files.
        """
        raise NotImplementedError()

    def size(self, name):
        """
        Returns the total size, in bytes, of the file specified by name.
        """
        raise NotImplementedError()

    def url(self, name):
        """
        Returns an absolute URL where the file's contents can be accessed
        directly by a Web browser.
        """
        raise NotImplementedError()

    def accessed_time(self, name):
        """
        Returns the last accessed time (as datetime object) of the file
        specified by name.
        """
        raise NotImplementedError()

    def created_time(self, name):
        """
        Returns the creation time (as datetime object) of the file
        specified by name.
        """
        raise NotImplementedError()

    def modified_time(self, name):
        """
        Returns the last modified time (as datetime object) of the file
        specified by name.
        """
        raise NotImplementedError()

class FileSystemStorage(Storage):
    """
    Standard filesystem storage
    """

    def __init__(self, location=None, base_url=None):
        if location is None:
            location = settings.MEDIA_ROOT
        if base_url is None:
            base_url = settings.MEDIA_URL
        self.location = os.path.abspath(location)
        self.base_url = base_url

    def _open(self, name, mode='rb'):
        return File(open(self.path(name), mode))

    def _save(self, name, content):
        full_path = self.path(name)

        directory = os.path.dirname(full_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        elif not os.path.isdir(directory):
            raise IOError("%s exists and is not a directory." % directory)

        # There's a potential race condition between get_available_name and
        # saving the file; it's possible that two threads might return the
        # same name, at which point all sorts of fun happens. So we need to
        # try to create the file, but if it already exists we have to go back
        # to get_available_name() and try again.

        while True:
            try:
                # This file has a file path that we can move.
                if hasattr(content, 'temporary_file_path'):
                    file_move_safe(content.temporary_file_path(), full_path)
                    content.close()

                # This is a normal uploadedfile that we can stream.
                else:
                    # This fun binary flag incantation makes os.open throw an
                    # OSError if the file already exists before we open it.
                    fd = os.open(full_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0))
                    try:
                        locks.lock(fd, locks.LOCK_EX)
                        for chunk in content.chunks():
                            os.write(fd, chunk)
                    finally:
                        locks.unlock(fd)
                        os.close(fd)
            except OSError, e:
                if e.errno == errno.EEXIST:
                    # Ooops, the file exists. We need a new file name.
                    name = self.get_available_name(name)
                    full_path = self.path(name)
                else:
                    raise
            else:
                # OK, the file save worked. Break out of the loop.
                break

        if settings.FILE_UPLOAD_PERMISSIONS is not None:
            os.chmod(full_path, settings.FILE_UPLOAD_PERMISSIONS)

        return name

    def delete(self, name):
        name = self.path(name)
        # If the file exists, delete it from the filesystem.
        if os.path.exists(name):
            os.remove(name)

    def exists(self, name):
        return os.path.exists(self.path(name))

    def listdir(self, path):
        path = self.path(path)
        directories, files = [], []
        for entry in os.listdir(path):
            if os.path.isdir(os.path.join(path, entry)):
                directories.append(entry)
            else:
                files.append(entry)
        return directories, files

    def path(self, name):
        try:
            path = safe_join(self.location, name)
        except ValueError:
            raise SuspiciousOperation("Attempted access to '%s' denied." % name)
        return os.path.normpath(path)

    def size(self, name):
        return os.path.getsize(self.path(name))

    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        return urlparse.urljoin(self.base_url, filepath_to_uri(name))

    def accessed_time(self, name):
        return datetime.fromtimestamp(os.path.getatime(self.path(name)))

    def created_time(self, name):
        return datetime.fromtimestamp(os.path.getctime(self.path(name)))

    def modified_time(self, name):
        return datetime.fromtimestamp(os.path.getmtime(self.path(name)))

def get_storage_class(import_path=None):
    if import_path is None:
        import_path = settings.DEFAULT_FILE_STORAGE
    try:
        dot = import_path.rindex('.')
    except ValueError:
        raise ImproperlyConfigured("%s isn't a storage module." % import_path)
    module, classname = import_path[:dot], import_path[dot+1:]
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured('Error importing storage module %s: "%s"' % (module, e))
    try:
        return getattr(mod, classname)
    except AttributeError:
        raise ImproperlyConfigured('Storage module "%s" does not define a "%s" class.' % (module, classname))

class DefaultStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class()()

default_storage = DefaultStorage()
