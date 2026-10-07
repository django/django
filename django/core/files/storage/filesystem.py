import os
from datetime import UTC, datetime
from tempfile import mkstemp
from urllib.parse import urljoin

from django.conf import settings
from django.core.files import File
from django.core.files.move import file_move_safe
from django.core.signals import setting_changed
from django.utils._os import safe_join, safe_makedirs
from django.utils.deconstruct import deconstructible
from django.utils.encoding import filepath_to_uri
from django.utils.functional import cached_property

from .base import Storage
from .mixins import StorageSettingsMixin


@deconstructible(path="django.core.files.storage.FileSystemStorage")
class FileSystemStorage(Storage, StorageSettingsMixin):
    """
    Standard filesystem storage
    """

    def __init__(
        self,
        location=None,
        base_url=None,
        file_permissions_mode=None,
        directory_permissions_mode=None,
        allow_overwrite=False,
    ):
        self._location = location
        self._base_url = base_url
        self._file_permissions_mode = file_permissions_mode
        self._directory_permissions_mode = directory_permissions_mode
        self._allow_overwrite = allow_overwrite
        setting_changed.connect(self._clear_cached_properties)

    @cached_property
    def base_location(self):
        return self._value_or_setting(self._location, settings.MEDIA_ROOT)

    @cached_property
    def location(self):
        return os.path.abspath(self.base_location)

    @cached_property
    def base_url(self):
        if self._base_url is not None and not self._base_url.endswith("/"):
            self._base_url += "/"
        return self._value_or_setting(self._base_url, settings.MEDIA_URL)

    @cached_property
    def file_permissions_mode(self):
        return self._value_or_setting(
            self._file_permissions_mode, settings.FILE_UPLOAD_PERMISSIONS
        )

    @cached_property
    def directory_permissions_mode(self):
        return self._value_or_setting(
            self._directory_permissions_mode, settings.FILE_UPLOAD_DIRECTORY_PERMISSIONS
        )

    @cached_property
    def umask(self):
        # There is no way to get a umask without setting it in the standard
        # library. This presents a thread safety issue if another thread
        # creates a file while umask is being retrieved.
        # 0o666 is the least bad alternative for a file to be created with.
        umask = os.umask(0o666)
        os.umask(umask)
        return umask

    def _open(self, name, mode="rb"):
        return File(open(self.path(name), mode))

    def _save(self, name, content):

        # A file that has a temporary file path and just needs copying.
        if hasattr(content, "temporary_file_path"):
            src_file_name = content.temporary_file_path()
        else:
            # This is a normal uploaded file that we can stream into a temp
            # file and eventually move over to destination.
            temp_fd, src_file_name = mkstemp()

            os.fchmod(temp_fd, 0o666 & ~self.umask)
            _file = None
            try:
                for chunk in content.chunks():
                    if _file is None:
                        mode = "wb" if isinstance(chunk, bytes) else "wt"
                        _file = os.fdopen(temp_fd, mode)
                    _file.write(chunk)
            finally:
                if _file is not None:
                    _file.close()
                else:
                    os.close(temp_fd)

        # Start moving the file to the final destination.

        full_path = self.path(name)

        # Create any intermediate directories that do not exist.
        directory = os.path.dirname(full_path)
        try:
            if self.directory_permissions_mode is not None:
                # Workaround because os.makedirs() doesn't apply the "mode"
                # argument to intermediate-level directories.
                # https://github.com/python/cpython/issues/86533
                safe_makedirs(directory, self.directory_permissions_mode, exist_ok=True)
            else:
                os.makedirs(directory, exist_ok=True)
        except FileExistsError:
            raise FileExistsError("%s exists and is not a directory." % directory)

        # There's a potential race condition between get_available_name and
        # moving the file; it's possible that two threads might return the
        # same name, at which point all sorts of fun happens. So we need to
        # try to create the file, but if it already exists we have to go back
        # to get_available_name() and try again.

        while True:
            try:
                file_move_safe(
                    src_file_name,
                    full_path,
                    allow_overwrite=self._allow_overwrite,
                )
            except FileExistsError:
                # A new name is needed if the file exists.
                name = self.get_available_name(name)
                full_path = self.path(name)
            else:
                # OK, the file save worked. Break out of the loop.
                break

        if self.file_permissions_mode is not None:
            os.chmod(full_path, self.file_permissions_mode)
        else:
            # file_move_safe may copy the file from one fs to another. In which
            # case we want to ensure that we're setting the old default
            # permissions.
            os.chmod(full_path, 0o666 & ~self.umask)

        # Ensure the saved path is always relative to the storage root.
        name = os.path.relpath(full_path, self.location)
        # Ensure the moved file has the same gid as the storage root.
        self._ensure_location_group_id(full_path)
        # Store filenames with forward slashes, even on Windows.
        return str(name).replace("\\", "/")

    def _ensure_location_group_id(self, full_path):
        if os.name == "posix":
            file_gid = os.stat(full_path).st_gid
            location_gid = os.stat(self.location).st_gid
            if file_gid != location_gid:
                try:
                    os.chown(full_path, uid=-1, gid=location_gid)
                except PermissionError:
                    pass

    def delete(self, name):
        if not name:
            raise ValueError("The name must be given to delete().")
        name = self.path(name)
        # If the file or directory exists, delete it from the filesystem.
        try:
            if os.path.isdir(name):
                os.rmdir(name)
            else:
                os.remove(name)
        except FileNotFoundError:
            # FileNotFoundError is raised if the file or directory was removed
            # concurrently.
            pass

    def is_name_available(self, name, max_length=None):
        if self._allow_overwrite:
            return not (max_length and len(name) > max_length)
        return super().is_name_available(name, max_length=max_length)

    def get_alternative_name(self, file_root, file_ext):
        if self._allow_overwrite:
            return f"{file_root}{file_ext}"
        return super().get_alternative_name(file_root, file_ext)

    def exists(self, name):
        return os.path.lexists(self.path(name))

    def listdir(self, path):
        path = self.path(path)
        directories, files = [], []
        with os.scandir(path) as entries:
            for entry in entries:
                if entry.is_dir():
                    directories.append(entry.name)
                else:
                    files.append(entry.name)
        return directories, files

    def path(self, name):
        return safe_join(self.location, name)

    def size(self, name):
        return os.path.getsize(self.path(name))

    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        url = filepath_to_uri(name)
        if url is not None:
            url = url.lstrip("/")
        return urljoin(self.base_url, url)

    def _datetime_from_timestamp(self, ts):
        """
        If timezone support is enabled, make an aware datetime object in UTC;
        otherwise make a naive one in the local timezone.
        """
        tz = UTC if settings.USE_TZ else None
        return datetime.fromtimestamp(ts, tz=tz)

    def get_accessed_time(self, name):
        return self._datetime_from_timestamp(os.path.getatime(self.path(name)))

    def get_created_time(self, name):
        return self._datetime_from_timestamp(os.path.getctime(self.path(name)))

    def get_modified_time(self, name):
        return self._datetime_from_timestamp(os.path.getmtime(self.path(name)))
