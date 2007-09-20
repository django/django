r"""

>>> from django.contrib.sessions.backends.db import SessionStore as DatabaseSession
>>> from django.contrib.sessions.backends.cache import SessionStore as CacheSession
>>> from django.contrib.sessions.backends.file import SessionStore as FileSession

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
"""

if __name__ == '__main__':
    import doctest
    doctest.testmod()
