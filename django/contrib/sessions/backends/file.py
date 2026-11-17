import datetime
import logging
import os
import shutil
import tempfile

from django.conf import settings
from django.contrib.sessions.backends.base import (
    VALID_KEY_CHARS,
    CreateError,
    SessionBase,
    UpdateError,
)
from django.contrib.sessions.exceptions import InvalidSessionKey
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation


class SessionStore(SessionBase):
    """
    Implement a file based session store.
    """

    def __init__(self, session_key=None):
        self.storage_path = self._get_storage_path()
        self.file_prefix = settings.SESSION_COOKIE_NAME
        super().__init__(session_key)

    @classmethod
    def _get_storage_path(cls):
        try:
            return cls._storage_path
        except AttributeError:
            storage_path = (
                getattr(settings, "SESSION_FILE_PATH", None) or tempfile.gettempdir()
            )
            # Make sure the storage path is valid.
            if not os.path.isdir(storage_path):
                raise ImproperlyConfigured(
                    "The session storage path %r doesn't exist. Please set your"
                    " SESSION_FILE_PATH setting to an existing directory in which"
                    " Django can store session data." % storage_path
                )

            cls._storage_path = storage_path
            return storage_path

    def _key_to_files(self, session_key=None):
        """
        Get the files that may be associated with this session key: the one
        named after its backend key and, while SESSION_STORE_KEY_HASH is
        "transition", the one named after the session key itself.
        """
        if session_key is None:
            session_key = self._get_or_create_session_key()

        # Make sure we're not vulnerable to directory traversal. Session keys
        # should always be md5s, so they should never contain directory
        # components.
        if not set(session_key).issubset(VALID_KEY_CHARS):
            raise InvalidSessionKey("Invalid characters in session key")

        return [
            os.path.join(self.storage_path, self.file_prefix + backend_key)
            for backend_key in self._get_backend_keys(session_key)
        ]

    def _key_to_file(self, session_key=None):
        """
        Get the file associated with this session key.
        """
        return self._key_to_files(session_key)[0]

    def _read_session_file(self):
        """
        Return the name and the content of the file of the current session.
        """
        session_files = self._key_to_files()
        if len(session_files) > 1:
            # While SESSION_STORE_KEY_HASH is "transition", the session may
            # still be in the file named after its session key. A concurrent
            # request may rename that file in the meantime, so the file named
            # after the hashed backend key is tried again.
            session_files.append(session_files[0])
        for session_file_name in session_files[:-1]:
            try:
                with open(session_file_name, encoding="ascii") as session_file:
                    return session_file_name, session_file.read()
            except FileNotFoundError:
                pass
        with open(session_files[-1], encoding="ascii") as session_file:
            return session_files[-1], session_file.read()

    def _move_session_file(self):
        """
        While SESSION_STORE_KEY_HASH is "transition", rename the file of the
        current session after its hashed backend key if it's still named after
        its session key. Return the file to save the session to, or None if the
        session has no file.
        """
        session_files = self._key_to_files()
        if len(session_files) == 1:
            return None
        try:
            os.replace(session_files[1], session_files[0])
        except FileNotFoundError:
            # A concurrent request may have just renamed the file.
            return session_files[0] if os.path.exists(session_files[0]) else None
        except OSError:
            # The file can't be renamed, for example because another process
            # has it open. Save the session where it is.
            return session_files[1]
        return session_files[0]

    def _last_modification(self, session_file_name=None):
        """
        Return the modification time of the file storing the session's content.
        """
        modification = os.stat(session_file_name or self._key_to_file()).st_mtime
        tz = datetime.UTC if settings.USE_TZ else None
        return datetime.datetime.fromtimestamp(modification, tz=tz)

    def _expiry_date(self, session_data, session_file_name=None):
        """
        Return the expiry time of the file storing the session's content.
        """
        return session_data.get("_session_expiry") or (
            self._last_modification(session_file_name)
            + datetime.timedelta(seconds=self.get_session_cookie_age())
        )

    def load(self):
        session_data = {}
        try:
            session_file_name, file_data = self._read_session_file()
            if session_file_name != self._key_to_file():
                # Have the session saved, which renames its file after its
                # hashed backend key.
                self.modified = True
            # Don't fail if there is no data in the session file.
            # We may have opened the empty placeholder file.
            if file_data:
                try:
                    session_data = self.decode(file_data)
                except (EOFError, SuspiciousOperation) as e:
                    if isinstance(e, SuspiciousOperation):
                        logger = logging.getLogger(
                            "django.security.%s" % e.__class__.__name__
                        )
                        logger.warning(str(e))
                    self.create()
                    session_file_name = None

                # Remove expired sessions.
                expiry_age = self.get_expiry_age(
                    expiry=self._expiry_date(session_data, session_file_name)
                )
                if expiry_age <= 0:
                    session_data = {}
                    self.delete()
                    self.create()
        except (OSError, SuspiciousOperation):
            self._session_key = None
        return session_data

    async def aload(self):
        return self.load()

    def create(self):
        while True:
            self._session_key = self._get_new_session_key()
            try:
                self.save(must_create=True)
            except CreateError:
                continue
            self.modified = True
            return

    async def acreate(self):
        return self.create()

    def save(self, must_create=False):
        if self.session_key is None:
            return self.create()
        # Get the session data now, before we start messing
        # with the file it is stored within.
        session_data = self._get_session(no_load=must_create)

        session_file_name = self._key_to_file()

        try:
            # Make sure the file exists. If it does not already exist, an
            # empty placeholder file is created.
            flags = os.O_WRONLY | getattr(os, "O_BINARY", 0)
            if must_create:
                flags |= os.O_EXCL | os.O_CREAT
            fd = os.open(session_file_name, flags)
            os.close(fd)
        except FileNotFoundError:
            if not must_create:
                session_file_name = self._move_session_file()
                if session_file_name is None:
                    raise UpdateError
        except FileExistsError:
            if must_create:
                raise CreateError

        # Write the session file without interfering with other threads
        # or processes. By writing to an atomically generated temporary
        # file and then using the atomic os.rename() to make the complete
        # file visible, we avoid having to lock the session file, while
        # still maintaining its integrity.
        #
        # Note: Locking the session file was explored, but rejected in part
        # because in order to be atomic and cross-platform, it required a
        # long-lived lock file for each session, doubling the number of
        # files in the session storage directory at any given time. This
        # rename solution is cleaner and avoids any additional overhead
        # when reading the session data, which is the more common case
        # unless SESSION_SAVE_EVERY_REQUEST = True.
        #
        # See ticket #8616.
        dir, prefix = os.path.split(session_file_name)

        try:
            output_file_fd, output_file_name = tempfile.mkstemp(
                dir=dir, prefix=prefix + "_out_"
            )
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
        except (EOFError, OSError):
            pass

    async def asave(self, must_create=False):
        return self.save(must_create=must_create)

    def exists(self, session_key):
        return any(
            os.path.exists(session_file_name)
            for session_file_name in self._key_to_files(session_key)
        )

    async def aexists(self, session_key):
        return self.exists(session_key)

    def delete(self, session_key=None):
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        # The file named after the session key comes first, so that the session
        # is found even if a concurrent request is renaming its file.
        for session_file_name in reversed(self._key_to_files(session_key)):
            try:
                os.unlink(session_file_name)
            except OSError:
                pass

    async def adelete(self, session_key=None):
        return self.delete(session_key=session_key)

    def _remove_if_expired(self, session_file_name):
        try:
            with open(session_file_name, encoding="ascii") as session_file:
                file_data = session_file.read()
            # Don't fail if there is no data in the session file.
            # We may have opened the empty placeholder file.
            if file_data:
                session_data = self.decode(file_data)
                expiry_age = self.get_expiry_age(
                    expiry=self._expiry_date(session_data, session_file_name)
                )
                if expiry_age <= 0:
                    os.unlink(session_file_name)
        except (EOFError, OSError, SuspiciousOperation, ValueError):
            # The file can't be read as a session, for example because it isn't
            # one.
            pass

    @classmethod
    def clear_expired(cls):
        storage_path = cls._get_storage_path()
        file_prefix = settings.SESSION_COOKIE_NAME
        backend_key_chars = set(VALID_KEY_CHARS + cls.hashed_key_prefix)

        for session_file in os.listdir(storage_path):
            if not session_file.startswith(file_prefix):
                continue
            backend_key = session_file.removeprefix(file_prefix)
            if settings.SESSION_STORE_KEY_HASH or backend_key.startswith(
                cls.hashed_key_prefix
            ):
                # The session key can't be derived from the name of a file
                # that's named after a hashed backend key, and it isn't the
                # backend key anymore, so the file is read directly.
                if set(backend_key).issubset(backend_key_chars):
                    cls()._remove_if_expired(os.path.join(storage_path, session_file))
                continue
            session = cls(backend_key)
            # When an expired session is loaded, its file is removed, and a
            # new file is immediately created. Prevent this by disabling
            # the create() method.
            session.create = lambda: None
            session.load()

    @classmethod
    async def aclear_expired(cls):
        cls.clear_expired()
