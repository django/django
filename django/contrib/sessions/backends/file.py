import datetime
import logging
import os
import shutil
import tempfile

from django.conf import settings
from django.contrib.sessions.backends.base import (
    VALID_KEY_CHARS, CreateError, HashingSessionBase, UpdateError,
)
from django.contrib.sessions.exceptions import InvalidSessionKey
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.utils import timezone


class SessionStore(HashingSessionBase):
    """
    Implement a file based session store.
    """

    @staticmethod
    def _get_file_prefix():
        return settings.SESSION_COOKIE_NAME

    @classmethod
    def _get_storage_path(cls):
        if not hasattr(cls, '_storage_path'):
            storage_path = getattr(settings, 'SESSION_FILE_PATH', None) or tempfile.gettempdir()
            # Make sure the storage path is valid.
            if not os.path.isdir(storage_path):
                raise ImproperlyConfigured(
                    "The session storage path %r doesn't exist. Please set your"
                    " SESSION_FILE_PATH setting to an existing directory in which"
                    " Django can store session data." % storage_path)

            cls._storage_path = storage_path

        return cls._storage_path

    @classmethod
    def _backend_key_to_file(cls, backend_key):
        # Make sure we're not vulnerable to directory traversal. Session keys
        # should always be md5s, so they should never contain directory
        # components.
        if not set(backend_key).issubset(VALID_KEY_CHARS):
            raise InvalidSessionKey(
                "Invalid characters in session key")

        return os.path.join(cls._get_storage_path(), cls._get_file_prefix() + backend_key)

    @staticmethod
    def _last_modification(file_path):
        """
        Return the modification time of the file storing the session's content.
        """
        modification = os.stat(file_path).st_mtime
        if settings.USE_TZ:
            modification = datetime.datetime.utcfromtimestamp(modification)
            return modification.replace(tzinfo=timezone.utc)
        return datetime.datetime.fromtimestamp(modification)

    @classmethod
    def _expiry_date(cls, session_data, file_path):
        """
        Return the expiry time of the file storing the session's content.
        """
        return session_data.get('_session_expiry') or (
            cls._last_modification(file_path) + datetime.timedelta(seconds=cls.get_session_cookie_age())
        )

    @classmethod
    def _load_session_data(cls, file_path):
        """
        Return dict with session data from specified file,
        return empty dict if specified file doesn't exits,
        return False if the file contains invalid content.
        """
        file_data = None

        try:
            with open(file_path, encoding='ascii') as session_file:
                file_data = session_file.read()
        except (OSError, SuspiciousOperation):
            return None

        # Don't fail if there is no data in the session file.
        # We may have opened the empty placeholder file.
        if not file_data:
            return {}

        try:
            session_data = cls().decode(file_data)
        except (EOFError, SuspiciousOperation) as e:
            if isinstance(e, SuspiciousOperation):
                logger = logging.getLogger('django.security.%s' % e.__class__.__name__)
                logger.warning(str(e))
            return False

        return session_data

    @staticmethod
    def _delete_file(file_path):
        try:
            os.unlink(file_path)
        except OSError:
            pass

    # SessionBase methods

    def load(self):
        """
        Load this session's data and return a dictionary.
        Return empty dictionary this session does not have
        a session or the session was not found. Reset the session
        if it has expired.
        """
        session_data = super().load()

        # return empty session if super().load() failed
        # and session key was reset
        if self.frontend_key is None:
            return {}

        # our _load_data will return False to indicate
        # invalid/corrupted session file. If that happens,
        # recreate our sessions file
        elif session_data == False:  # noqa: E712
            self.create()
            session_data = {}

        if session_data is None:
            session_data = {}

        # Remove expired sessions.
        backend_key = self.get_backend_key(self._get_or_create_frontend_key())
        expiry_date = self._expiry_date(session_data, self._backend_key_to_file(backend_key))
        expiry_age = self.get_expiry_age(expiry=expiry_date)
        if expiry_age <= 0:
            session_data = {}
            self.delete()
            self.create()

        return session_data

    @classmethod
    def _load_data(cls, backend_key):
        """
        Return dict with session data from file corresponding to the
        given backend_key. Return empty dict if no corresponding file
        is found, return ``False`` if the file contains invalid content.
        """
        return cls._load_session_data(cls._backend_key_to_file(backend_key))

    @classmethod
    def _save(cls, backend_key, session_data, must_create=False):
        session_file_name = cls._backend_key_to_file(backend_key)

        try:
            # Make sure the file exists.  If it does not already exist, an
            # empty placeholder file is created.
            flags = os.O_WRONLY | getattr(os, 'O_BINARY', 0)
            if must_create:
                flags |= os.O_EXCL | os.O_CREAT
            fd = os.open(session_file_name, flags)
            os.close(fd)
        except FileNotFoundError:
            if not must_create:
                raise UpdateError
        except FileExistsError:
            if must_create:
                raise CreateError

        # Write the session file without interfering with other threads
        # or processes.  By writing to an atomically generated temporary
        # file and then using the atomic os.rename() to make the complete
        # file visible, we avoid having to lock the session file, while
        # still maintaining its integrity.
        #
        # Note: Locking the session file was explored, but rejected in part
        # because in order to be atomic and cross-platform, it required a
        # long-lived lock file for each session, doubling the number of
        # files in the session storage directory at any given time.  This
        # rename solution is cleaner and avoids any additional overhead
        # when reading the session data, which is the more common case
        # unless SESSION_SAVE_EVERY_REQUEST = True.
        #
        # See ticket #8616.
        dir, prefix = os.path.split(session_file_name)

        try:
            output_file_fd, output_file_name = tempfile.mkstemp(dir=dir, prefix=prefix + '_out_')
            renamed = False
            try:
                try:
                    os.write(output_file_fd, cls._encode(session_data).encode())
                finally:
                    os.close(output_file_fd)

                # This will atomically rename the file (os.rename) if the OS
                # supports it. Otherwise this will result in a shutil.copy2
                # and os.unlink (for example on Windows). See #9084.
                shutil.move(output_file_name, session_file_name)
                renamed = True
            finally:
                if not renamed:
                    os.unlink(output_file_name)
        except (EOFError, OSError):
            pass
        pass

    @classmethod
    def _exists(cls, backend_key):
        return os.path.exists(cls._backend_key_to_file(backend_key))

    @classmethod
    def _delete(cls, backend_key):
        cls._delete_file(cls._backend_key_to_file(backend_key))

    @classmethod
    def clear_expired(cls):
        storage_path = cls._get_storage_path()
        file_prefix = cls._get_file_prefix()

        for session_file in os.listdir(storage_path):
            if not session_file.startswith(file_prefix):
                continue

            file_path = os.path.join(storage_path, session_file)
            session_data = cls._load_session_data(file_path)
            if session_data:
                expiry_age = cls().get_expiry_age(expiry=cls._expiry_date(session_data, file_path=file_path))

                if expiry_age <= 0:
                    session_data = {}
                    cls._delete_file(file_path)
