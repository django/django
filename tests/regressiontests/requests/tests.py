"""
>>> from django.http import HttpRequest
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
"""
