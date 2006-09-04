# tests that db settings can change between requests
import copy
import os
import unittest
from django.conf import settings, UserSettingsHolder
from django.core.handlers.wsgi import WSGIHandler
from django.db import models, model_connection_name, _default, connection
from django.http import HttpResponse
from regressiontests.request_isolation.models import *


# helpers
class MockHandler(WSGIHandler):

    def __init__(self, test):
        self.test = test
        super(MockHandler, self).__init__()
        
    def get_response(self, path, request):
        # debug("mock handler answering %s, %s", path, request)
        return HttpResponse(self.test(path, request))


def debug(*arg):
    pass
    # msg, arg = arg[0], arg[1:]
    # print msg % arg


def start_response(code, headers):
    debug("start response: %s %s", code, headers)
    pass

# tests
class TestRequestIsolation(unittest.TestCase):

    def setUp(self):
        debug("setup")
        self.settings = settings._target
        settings._target = UserSettingsHolder(copy.deepcopy(settings._target))
        settings.OTHER_DATABASES['_a']['MODELS'] = ['ri.MX']
        settings.OTHER_DATABASES['_b']['MODELS'] = ['ri.MY']

    def tearDown(self):
        debug("teardown")
        settings._target = self.settings

    def testRequestIsolation(self):
        env = os.environ.copy()
        env['PATH_INFO'] = '/'
        env['REQUEST_METHOD'] = 'GET'

        def request_one(path, request):
            """Start out with settings as originally configured"""
            self.assertEqual(model_connection_name(MX), '_a')
            self.assertEqual(
                MX._default_manager.db.connection.settings.DATABASE_NAME,
                settings.OTHER_DATABASES['_a']['DATABASE_NAME'])
            self.assertEqual(model_connection_name(MY), '_b')
            self.assertEqual(
                MY._default_manager.db.connection.settings.DATABASE_NAME,
                settings.OTHER_DATABASES['_b']['DATABASE_NAME'])

        def request_two(path, request):
            """Between the first and second requests, settings change to assign
            model MY to a different connection
            """
            self.assertEqual(model_connection_name(MX), '_a')
            self.assertEqual(
                MX._default_manager.db.connection.settings.DATABASE_NAME,
                settings.OTHER_DATABASES['_a']['DATABASE_NAME'])
            self.assertEqual(model_connection_name(MY), _default)
            self.assertEqual(
                MY._default_manager.db.connection.settings.DATABASE_NAME,
                settings.DATABASE_NAME)

        def request_three(path, request):
            """Between the 2nd and 3rd requests, the settings at the names in
            OTHER_DATABASES have changed.
            """
            self.assertEqual(model_connection_name(MX), '_b')
            self.assertEqual(
                MX._default_manager.db.connection.settings.DATABASE_NAME,
                settings.OTHER_DATABASES['_b']['DATABASE_NAME'])
            self.assertEqual(model_connection_name(MY), '_a')
            self.assertEqual(
                MY._default_manager.db.connection.settings.DATABASE_NAME,
                settings.OTHER_DATABASES['_a']['DATABASE_NAME'])
    
        MockHandler(request_one)(env, start_response)

        settings.OTHER_DATABASES['_b']['MODELS'] = []
        MockHandler(request_two)(env, start_response)

        settings.OTHER_DATABASES['_b']['MODELS'] = ['ri.MY']
        settings.OTHER_DATABASES['_b'], \
            settings.OTHER_DATABASES['_a'] = \
            settings.OTHER_DATABASES['_a'], \
            settings.OTHER_DATABASES['_b']
        MockHandler(request_three)(env, start_response)
