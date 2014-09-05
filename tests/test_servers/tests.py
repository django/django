# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
from wsgiref.simple_server import make_server, demo_app

from django.core.handlers.wsgi import WSGIRequest
from django.core.servers.basehttp import WSGIRequestHandler
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils.six import StringIO


class WSGIRequestHandlerTestCase(TestCase):
    def test_log_message(self):
        server = make_server('', 8000, demo_app, handler_class=WSGIRequestHandler)
        environ = RequestFactory().get('/').environ
        request = WSGIRequest(environ)

        request.makefile = lambda *args, **kwargs: StringIO()
        handler = WSGIRequestHandler(request, '192.168.0.2', server)

        _stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            handler.log_message("non ascii characters will follow: %s %s", "ā", "ü")
        finally:
            sys.stderr = _stderr
