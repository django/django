import errno
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
                file_data = session_file.read()
                # Don't fail if there is no data in the session file.
                # We may have opened the empty placeholder file.
                if file_data:
                    try:
                        session_data = self.decode(file_data)
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
        # Get the session data now, before we start messing
        # with the file it is stored within.
        session_data = self._get_session(no_load=must_create)

        session_file_name = self._key_to_file()

        try:
            # Make sure the file exists.  If it does not already exist, an
            # empty placeholder file is created.
            flags = os.O_WRONLY | os.O_CREAT | getattr(os, 'O_BINARY', 0)
            if must_create:
                flags |= os.O_EXCL
            fd = os.open(session_file_name, flags)
            os.close(fd)

        except OSError, e:
            if must_create and e.errno == errno.EEXIST:
                raise CreateError
            raise

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
            output_file_fd, output_file_name = tempfile.mkstemp(dir=dir,
                prefix=prefix + '_out_')
            renamed = False
            try:
                try:
                    os.write(output_file_fd, self.encode(session_data))
                finally:
                    os.close(output_file_fd)
                os.rename(output_file_name, session_file_name)
                renamed = True
            finally:
                if not renamed:
                    os.unlink(output_file_name)

        except (OSError, IOError, EOFError):
            pass

    def exists(self, session_key):
        if os.path.exists(self._key_to_file(session_key)):
            return True
        return False

    def delete(self, session_key=None):
        if session_key is None:
            if self._session_key is None:
                return
            session_key = self._session_key
        try:
            os.unlink(self._key_to_file(session_key))
        except OSError:
            pass

    def clean(self):
        pass
