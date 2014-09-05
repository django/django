# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
from wsgiref.simple_server import make_server, demo_app

from django.core.handlers.wsgi import WSGIRequest
from django.core.servers.basehttp import WSGIRequestHandler
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils.six import BytesIO, StringIO


class WSGIRequestHandlerTestCase(TestCase):
    def test_https(self):
        server = make_server('', 8000, demo_app, handler_class=WSGIRequestHandler)
        environ = RequestFactory().get('/').environ
        request = WSGIRequest(environ)

        request.makefile = lambda *args, **kwargs: BytesIO()
        handler = WSGIRequestHandler(request, '192.168.0.2', server)

        _stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            handler.log_message("GET %s %s", str('\x16\x03'), "4")
            sys.stderr.seek(0)
            error = sys.stderr.read()
            self.assertTrue("You're accessing the developement server over HTTPS, but it only supports HTTP." in error)
        finally:
            sys.stderr = _stderr
