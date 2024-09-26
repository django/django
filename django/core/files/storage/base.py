import os
import pathlib

from django.core.exceptions import SuspiciousFileOperation
from django.core.files import File
from django.core.files.utils import validate_file_name
from django.utils.crypto import get_random_string
from django.utils.text import get_valid_filename


class Storage:
    """
    A base storage class, providing some default behaviors that all other
    storage systems can inherit or override, as necessary.
    """

    # The following methods represent a public interface to private methods.
    # These shouldn't be overridden by subclasses unless absolutely necessary.

    def open(self, name, mode="rb"):
        """Retrieve the specified file from storage."""
        return self._open(name, mode)

    def save(self, name, content, max_length=None):
        """
        Save new content to the file specified by name. The content should be
        a proper File object or any Python file-like object, ready to be read
        from the beginning.
        """
        # Get the proper name for the file, as it will actually be saved.
        if name is None:
            name = content.name

        if not hasattr(content, "chunks"):
            content = File(content, name)

        # Ensure that the name is valid, before and after having the storage
        # system potentially modifying the name. This duplicates the check made
        # inside `get_available_name` but it's necessary for those cases where
        # `get_available_name` is overriden and validation is lost.
        validate_file_name(name, allow_relative_path=True)

        # Potentially find a different name depending on storage constraints.
        name = self.get_available_name(name, max_length=max_length)
        # Validate the (potentially) new name.
        validate_file_name(name, allow_relative_path=True)

        # The save operation should return the actual name of the file saved.
        name = self._save(name, content)
        # Ensure that the name returned from the storage system is still valid.
        validate_file_name(name, allow_relative_path=True)
        return name

    def is_name_available(self, name, max_length=None):
        exceeds_max_length = max_length and len(name) > max_length
        return not self.exists(name) and not exceeds_max_length

    # These methods are part of the public API, with default implementations.

    def get_valid_name(self, name):
        """
        Return a filename, based on the provided filename, that's suitable for
        use in the target storage system.
        """
        return get_valid_filename(name)

    def get_alternative_name(self, file_root, file_ext):
        """
        Return an alternative filename, by adding an underscore and a random 7
        character alphanumeric string (before the file extension, if one
        exists) to the filename.
        """
        return "%s_%s%s" % (file_root, get_random_string(7), file_ext)

    def get_available_name(self, name, max_length=None):
        """
        Return a filename that's free on the target storage system and
        available for new content to be written to.
        """
        name = str(name).replace("\\", "/")
        dir_name, file_name = os.path.split(name)
        if ".." in pathlib.PurePath(dir_name).parts:
            raise SuspiciousFileOperation(
                "Detected path traversal attempt in '%s'" % dir_name
            )
        validate_file_name(file_name)
        file_ext = "".join(pathlib.PurePath(file_name).suffixes)
        file_root = file_name.removesuffix(file_ext)
        # If the filename is not available, generate an alternative
        # filename until one is available.
        # Truncate original name if required, so the new filename does not
        # exceed the max_length.
        while not self.is_name_available(name, max_length=max_length):
            # file_ext includes the dot.
            name = os.path.join(
                dir_name, self.get_alternative_name(file_root, file_ext)
            )
            if max_length is None:
                continue
            # Truncate file_root if max_length exceeded.
            truncation = len(name) - max_length
            if truncation > 0:
                file_root = file_root[:-truncation]
                # Entire file_root was truncated in attempt to find an
                # available filename.
                if not file_root:
                    raise SuspiciousFileOperation(
                        'Storage can not find an available filename for "%s". '
                        "Please make sure that the corresponding file field "
                        'allows sufficient "max_length".' % name
                    )
                name = os.path.join(
                    dir_name, self.get_alternative_name(file_root, file_ext)
                )
        return name

    def generate_filename(self, filename):
        """
        Validate the filename by calling get_valid_name() and return a filename
        to be passed to the save() method.
        """
        filename = str(filename).replace("\\", "/")
        # `filename` may include a path as returned by FileField.upload_to.
        dirname, filename = os.path.split(filename)
        if ".." in pathlib.PurePath(dirname).parts:
            raise SuspiciousFileOperation(
                "Detected path traversal attempt in '%s'" % dirname
            )
        return os.path.normpath(os.path.join(dirname, self.get_valid_name(filename)))

    def path(self, name):
        """
        Return a local filesystem path where the file can be retrieved using
        Python's built-in open() function. Storage systems that can't be
        accessed using open() should *not* implement this method.
        """
        raise NotImplementedError("This backend doesn't support absolute paths.")

    # The following methods form the public API for storage systems, but with
    # no default implementations. Subclasses must implement *all* of these.

    def delete(self, name):
        """
        Delete the specified file from the storage system.
        """
        raise NotImplementedError(
            "subclasses of Storage must provide a delete() method"
        )

    def exists(self, name):
        """
        Return True if a file referenced by the given name already exists in the
        storage system, or False if the name is available for a new file.
        """
        raise NotImplementedError(
            "subclasses of Storage must provide an exists() method"
        )

    def listdir(self, path):
        """
        List the contents of the specified path. Return a 2-tuple of lists:
        the first item being directories, the second item being files.
        """
        raise NotImplementedError(
            "subclasses of Storage must provide a listdir() method"
        )

    def size(self, name):
        """
        Return the total size, in bytes, of the file specified by name.
        """
        raise NotImplementedError("subclasses of Storage must provide a size() method")

    def url(self, name):
        """
        Return an absolute URL where the file's contents can be accessed
        directly by a web browser.
        """
        raise NotImplementedError("subclasses of Storage must provide a url() method")

    def get_accessed_time(self, name):
        """
        Return the last accessed time (as a datetime) of the file specified by
        name. The datetime will be timezone-aware if USE_TZ=True.
        """
        raise NotImplementedError(
            "subclasses of Storage must provide a get_accessed_time() method"
        )

    def get_created_time(self, name):
        """
        Return the creation time (as a datetime) of the file specified by name.
        The datetime will be timezone-aware if USE_TZ=True.
        """
        raise NotImplementedError(
            "subclasses of Storage must provide a get_created_time() method"
        )

    def get_modified_time(self, name):
        """
        Return the last modified time (as a datetime) of the file specified by
        name. The datetime will be timezone-aware if USE_TZ=True.
        """
        raise NotImplementedError(
            "subclasses of Storage must provide a get_modified_time() method"
        )
