import os
import tempfile
from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase
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
            raise ImproperlyConfigured("The session storage path %r doesn't exist. "\
                                       "Please set your SESSION_FILE_PATH setting "\
                                       "to an existing directory in which Django "\
                                       "can store session data." % self.storage_path)

        self.file_prefix = settings.SESSION_COOKIE_NAME
        super(SessionStore, self).__init__(session_key)

    def _key_to_file(self, session_key=None):
        """
        Get the file associated with this session key.
        """
        if session_key is None:
            session_key = self.session_key

        # Make sure we're not vulnerable to directory traversal. Session keys
        # should always be md5s, so they should never contain directory components.
        if os.path.sep in session_key:
            raise SuspiciousOperation("Invalid characters (directory components) in session key")

        return os.path.join(self.storage_path, self.file_prefix + session_key)

    def load(self):
        session_data = {}
        try:
            session_file = open(self._key_to_file(), "rb")
            try:
                try:
                    session_data = self.decode(session_file.read())
                except(EOFError, SuspiciousOperation):
                    self._session_key = self._get_new_session_key()
                    self._session_cache = {}
                    self.save()
                    # Ensure the user is notified via a new cookie.
                    self.modified = True
            finally:
                session_file.close()
        except(IOError):
            pass
        return session_data

    def save(self):
        try:
            f = open(self._key_to_file(self.session_key), "wb")
            try:
                f.write(self.encode(self._session))
            finally:
                f.close()
        except(IOError, EOFError):
            pass

    def exists(self, session_key):
        if os.path.exists(self._key_to_file(session_key)):
            return True
        return False

    def delete(self, session_key):
        try:
            os.unlink(self._key_to_file(session_key))
        except OSError:
            pass

    def clean(self):
        pass
