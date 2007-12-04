r"""

>>> from django.conf import settings
>>> from django.contrib.sessions.backends.db import SessionStore as DatabaseSession
>>> from django.contrib.sessions.backends.cache import SessionStore as CacheSession
>>> from django.contrib.sessions.backends.file import SessionStore as FileSession
>>> from django.contrib.sessions.backends.base import SessionBase

>>> db_session = DatabaseSession()
>>> db_session.modified
False
>>> db_session['cat'] = "dog"
>>> db_session.modified
True
>>> db_session.pop('cat')
'dog'
>>> db_session.pop('some key', 'does not exist')
'does not exist'
>>> db_session.save()
>>> db_session.exists(db_session.session_key)
True
>>> db_session.delete(db_session.session_key)
>>> db_session.exists(db_session.session_key)
False

>>> file_session = FileSession()
>>> file_session.modified
False
>>> file_session['cat'] = "dog"
>>> file_session.modified
True
>>> file_session.pop('cat')
'dog'
>>> file_session.pop('some key', 'does not exist')
'does not exist'
>>> file_session.save()
>>> file_session.exists(file_session.session_key)
True
>>> file_session.delete(file_session.session_key)
>>> file_session.exists(file_session.session_key)
False

# Make sure the file backend checks for a good storage dir
>>> settings.SESSION_FILE_PATH = "/if/this/directory/exists/you/have/a/weird/computer"
>>> FileSession()
Traceback (innermost last):
    ...
ImproperlyConfigured: The session storage path '/if/this/directory/exists/you/have/a/weird/computer' doesn't exist. Please set your SESSION_FILE_PATH setting to an existing directory in which Django can store session data.

>>> cache_session = CacheSession()
>>> cache_session.modified
False
>>> cache_session['cat'] = "dog"
>>> cache_session.modified
True
>>> cache_session.pop('cat')
'dog'
>>> cache_session.pop('some key', 'does not exist')
'does not exist'
>>> cache_session.save()
>>> cache_session.delete(cache_session.session_key)
>>> cache_session.exists(cache_session.session_key)
False

>>> s = SessionBase()
>>> s._session['some key'] = 'exists' # Pre-populate the session with some data
>>> s.accessed = False   # Reset to pretend this wasn't accessed previously

>>> s.accessed, s.modified
(False, False)

>>> s.pop('non existant key', 'does not exist')
'does not exist'
>>> s.accessed, s.modified
(True, False)

>>> s.setdefault('foo', 'bar')
'bar'
>>> s.setdefault('foo', 'baz')
'bar'

>>> s.accessed = False  # Reset the accessed flag

>>> s.pop('some key')
'exists'
>>> s.accessed, s.modified
(True, True)

>>> s.pop('some key', 'does not exist')
'does not exist'
"""

if __name__ == '__main__':
    import doctest
    doctest.testmod()
