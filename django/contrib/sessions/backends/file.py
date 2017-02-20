import datetime
import logging
import os
import shutil
import tempfile

from django.conf import settings
from django.contrib.sessions.backends.base import (
    VALID_KEY_CHARS, CreateError, SessionBase, UpdateError,
)
from django.contrib.sessions.exceptions import InvalidSessionKey
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.utils import timezone
from django.utils.encoding import force_text


class SessionStore(SessionBase):
    """
    Implement a file based session store.
    """
    def __init__(self, session_key=None):
        self.storage_path = type(self)._get_storage_path()
        self.file_prefix = settings.SESSION_COOKIE_NAME
        super().__init__(session_key)

    @classmethod
    def _get_storage_path(cls):
        try:
            return cls._storage_path
        except AttributeError:
            storage_path = getattr(settings, "SESSION_FILE_PATH", None)
            if not storage_path:
                storage_path = tempfile.gettempdir()

            # Make sure the storage path is valid.
            if not os.path.isdir(storage_path):
                raise ImproperlyConfigured(
                    "The session storage path %r doesn't exist. Please set your"
                    " SESSION_FILE_PATH setting to an existing directory in which"
                    " Django can store session data." % storage_path)

            cls._storage_path = storage_path
            return storage_path

    def _key_to_file(self, session_key=None):
        """
        Get the file associated with this session key.
        """
        if session_key is None:
            session_key = self._get_or_create_session_key()

        # Make sure we're not vulnerable to directory traversal. Session keys
        # should always be md5s, so they should never contain directory
        # components.
        if not set(session_key).issubset(set(VALID_KEY_CHARS)):
            raise InvalidSessionKey(
                "Invalid characters in session key")

        return os.path.join(self.storage_path, self.file_prefix + session_key)

    def _last_modification(self):
        """
        Return the modification time of the file storing the session's content.
        """
        modification = os.stat(self._key_to_file()).st_mtime
        if settings.USE_TZ:
            modification = datetime.datetime.utcfromtimestamp(modification)
            modification = modification.replace(tzinfo=timezone.utc)
        else:
            modification = datetime.datetime.fromtimestamp(modification)
        return modification

    def _expiry_date(self, session_data):
        """
        Return the expiry time of the file storing the session's content.
        """
        expiry = session_data.get('_session_expiry')
        if not expiry:
            expiry = self._last_modification() + datetime.timedelta(seconds=settings.SESSION_COOKIE_AGE)
        return expiry

    def load(self):
        session_data = {}
        try:
            with open(self._key_to_file(), "rb") as session_file:
                file_data = session_file.read()
            # Don't fail if there is no data in the session file.
            # We may have opened the empty placeholder file.
            if file_data:
                try:
                    session_data = self.decode(file_data)
                except (EOFError, SuspiciousOperation) as e:
                    if isinstance(e, SuspiciousOperation):
                        logger = logging.getLogger('django.security.%s' % e.__class__.__name__)
                        logger.warning(force_text(e))
                    self.create()

                # Remove expired sessions.
                expiry_age = self.get_expiry_age(expiry=self._expiry_date(session_data))
                if expiry_age <= 0:
                    session_data = {}
                    self.delete()
                    self.create()
        except (IOError, SuspiciousOperation):
            self._session_key = None
        return session_data

    def create(self):
        while True:
            self._session_key = self._get_new_session_key()
            try:
                self.save(must_create=True)
            except CreateError:
                continue
            self.modified = True
            return

    def save(self, must_create=False):
        if self.session_key is None:
            return self.create()
        # Get the session data now, before we start messing
        # with the file it is stored within.
        session_data = self._get_session(no_load=must_create)

        session_file_name = self._key_to_file()

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
                    os.write(output_file_fd, self.encode(session_data).encode())
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

        except (OSError, IOError, EOFError):
            pass

    def exists(self, session_key):
        return os.path.exists(self._key_to_file(session_key))

    def delete(self, session_key=None):
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        try:
            os.unlink(self._key_to_file(session_key))
        except OSError:
            pass

    def clean(self):
        pass

    @classmethod
    def clear_expired(cls):
        storage_path = cls._get_storage_path()
        file_prefix = settings.SESSION_COOKIE_NAME

        for session_file in os.listdir(storage_path):
            if not session_file.startswith(file_prefix):
                continue
            session_key = session_file[len(file_prefix):]
            session = cls(session_key)
            # When an expired session is loaded, its file is removed, and a
            # new file is immediately created. Prevent this by disabling
            # the create() method.
            session.create = lambda: None
            session.load()
