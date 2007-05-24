r"""
>>> s = SessionWrapper(None)

Inject data into the session cache.
>>> s._session_cache = {}
>>> s._session_cache['some key'] = 'exists'

>>> s.pop('some key')
'exists'

>>> s.pop('some key', 'does not exist')
'does not exist'
"""

from django.contrib.sessions.middleware import SessionWrapper

if __name__ == '__main__':
    import doctest
    doctest.testmod()
