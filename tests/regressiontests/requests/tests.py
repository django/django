"""
>>> from django.http import HttpRequest, HttpResponse
>>> print repr(HttpRequest())
<HttpRequest
GET:{},
POST:{},
COOKIES:{},
META:{}>

>>> from django.core.handlers.wsgi import WSGIRequest
>>> print repr(WSGIRequest({'PATH_INFO': 'bogus', 'REQUEST_METHOD': 'bogus'}))
<WSGIRequest
GET:<QueryDict: {}>,
POST:<QueryDict: {}>,
COOKIES:{},
META:{...}>

>>> from django.core.handlers.modpython import ModPythonRequest
>>> class FakeModPythonRequest(ModPythonRequest):
...    def __init__(self, *args, **kwargs):
...        super(FakeModPythonRequest, self).__init__(*args, **kwargs)
...        self._get = self._post = self._meta = self._cookies = {}
>>> class Dummy:
...     def get_options(self):
...         return {}
>>> req = Dummy()
>>> req.uri = 'bogus'
>>> print repr(FakeModPythonRequest(req))
<ModPythonRequest
path:bogus,
GET:{},
POST:{},
COOKIES:{},
META:{}>

>>> from django.http import parse_cookie
>>> parse_cookie('invalid:key=true')
{}

>>> request = HttpRequest()
>>> print request.build_absolute_uri(location="https://www.example.com/asdf")
https://www.example.com/asdf
>>> request.get_host = lambda: 'www.example.com'
>>> request.path = ''
>>> print request.build_absolute_uri(location="/path/with:colons")
http://www.example.com/path/with:colons


# Test cookie datetime expiration logic
>>> from datetime import datetime, timedelta
>>> import time
>>> delta = timedelta(seconds=10)
>>> response = HttpResponse()
>>> expires = datetime.utcnow() + delta

# There is a timing weakness in this test; The
# expected result for max-age requires that there be
# a very slight difference between the evaluated expiration
# time, and the time evaluated in set_cookie(). If this
# difference doesn't exist, the cookie time will be
# 1 second larger. To avoid the problem, put in a quick sleep,
# which guarantees that there will be a time difference.
>>> time.sleep(0.001)
>>> response.set_cookie('datetime', expires=expires)
>>> datetime_cookie = response.cookies['datetime']
>>> datetime_cookie['max-age']
10
>>> response.set_cookie('datetime', expires=datetime(2028, 1, 1, 4, 5, 6))
>>> response.cookies['datetime']['expires']
'Sat, 01-Jan-2028 04:05:06 GMT'

# Test automatically setting cookie expires if only max_age is provided
>>> response.set_cookie('max_age', max_age=10)
>>> max_age_cookie = response.cookies['max_age']
>>> max_age_cookie['max-age']
10
>>> from django.utils.http import cookie_date
>>> import time
>>> max_age_cookie['expires'] == cookie_date(time.time()+10)
True
"""
