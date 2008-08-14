import os
import tempfile

from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase, CreateError
from django.core.exceptions import SuspiciousOperation, ImproperlyConfigured


class SessionStore(SessionBase):
    """
    Implements a file based session store.
    """
    def __init__(self, session_key=None):
        self.storage_path = getattr(settings, "SESSION_FILE_PATH", None)
        if not self.storage_path:
            self.storage_path = tempfile.gettempdir()

        # Make sure the storage path is valid.
        if not os.path.isdir(self.storage_path):
            raise ImproperlyConfigured(
                "The session storage path %r doesn't exist. Please set your"
                " SESSION_FILE_PATH setting to an existing directory in which"
                " Django can store session data." % self.storage_path)

        self.file_prefix = settings.SESSION_COOKIE_NAME
        super(SessionStore, self).__init__(session_key)

    def _key_to_file(self, session_key=None):
        """
        Get the file associated with this session key.
        """
        if session_key is None:
            session_key = self.session_key

        # Make sure we're not vulnerable to directory traversal. Session keys
        # should always be md5s, so they should never contain directory
        # components.
        if os.path.sep in session_key:
            raise SuspiciousOperation(
                "Invalid characters (directory components) in session key")

        return os.path.join(self.storage_path, self.file_prefix + session_key)

    def load(self):
        session_data = {}
        try:
            session_file = open(self._key_to_file(), "rb")
            try:
                try:
                    session_data = self.decode(session_file.read())
                except (EOFError, SuspiciousOperation):
                    self.create()
            finally:
                session_file.close()
        except IOError:
            pass
        return session_data

    def create(self):
        while True:
            self._session_key = self._get_new_session_key()
            try:
                self.save(must_create=True)
            except CreateError:
                continue
            self.modified = True
            self._session_cache = {}
            return

    def save(self, must_create=False):
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_BINARY', 0)
        if must_create:
            flags |= os.O_EXCL
        # Because this may trigger a load from storage, we must do it before
        # truncating the file to save.
        session_data = self._get_session(no_load=must_create)
        try:
            fd = os.open(self._key_to_file(self.session_key), flags)
            try:
                os.write(fd, self.encode(session_data))
            finally:
                os.close(fd)
        except OSError, e:
            if must_create and e.errno == errno.EEXIST:
                raise CreateError
            raise
        except (IOError, EOFError):
            pass

    def exists(self, session_key):
        if os.path.exists(self._key_to_file(session_key)):
            return True
        return False

    def delete(self, session_key=None):
        if session_key is None:
            session_key = self._session_key
        try:
            os.unlink(self._key_to_file(session_key))
        except OSError:
            pass

    def clean(self):
        pass
