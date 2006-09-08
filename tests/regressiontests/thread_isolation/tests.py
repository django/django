# tests that db settings can be different in different threads
#
#
#    What's going on here:
#
#    Simulating multiple web requests in a threaded environment, one in
#    which settings are different for each request. So we replace
#    django.conf.settings with a thread local, with different
#    configurations in each thread, and then fire off three
#    simultaneous requests (using a condition to sync them up), and
#    test that each thread sees its own settings and the models in each
#    thread attempt to connect to the correct database as per their
#    settings.
#


import copy
import os
import sys
import threading
import unittest
from thread import get_ident

from django.conf import settings, UserSettingsHolder
from django.core.handlers.wsgi import WSGIHandler
from django.db import model_connection_name, _default, connection, connections
from regressiontests.request_isolation.tests import MockHandler
from regressiontests.thread_isolation.models import *

try:
    # Only exists in Python 2.4+
    from threading import local
except ImportError:
    # Import copy of _thread_local.py from Python 2.4
    from django.utils._threading_local import local

# helpers
EV = threading.Event()

class LocalSettings:
    """Settings holder that allows thread-local overrides of defaults.
    """
    def __init__(self, defaults):
        self._defaults = defaults
        self._local = local()

    def __getattr__(self, attr):
        if attr in ('_defaults', '_local'):
            return self.__dict__[attr]
        _local = self.__dict__['_local']
        _defaults = self.__dict__['_defaults']
        debug("LS get %s (%s)", attr, hasattr(_local, attr))
        if not hasattr(_local, attr):
            # Make sure everything we return is the local version; this
            # avoids sets to deep datastructures overwriting the defaults
            setattr(_local, attr, copy.deepcopy(getattr(_defaults, attr)))
        return getattr(_local, attr)

    def __setattr__(self, attr, val):
        if attr in ('_defaults', '_local'):
            self.__dict__[attr] = val
        else:
            debug("LS set local %s = %s", attr, val)
            setattr(self.__dict__['_local'], attr, val)

def thread_two(func, *arg):
    def start():
        # from django.conf import settings
        settings.OTHER_DATABASES['_b']['MODELS'] = []

        debug("t2 ODB: %s", settings.OTHER_DATABASES)
        debug("t2 waiting")
        EV.wait(2.0)
        func(*arg)
        debug("t2 complete")
    t2 = threading.Thread(target=start)
    t2.start()
    return t2

def thread_three(func, *arg):
    def start():
        # from django.conf import settings            
        settings.OTHER_DATABASES['_b']['MODELS'] = ['ti.MY']
        settings.OTHER_DATABASES['_b'], \
            settings.OTHER_DATABASES['_a'] = \
            settings.OTHER_DATABASES['_a'], \
            settings.OTHER_DATABASES['_b']

        settings.DATABASE_NAME = \
            settings.OTHER_DATABASES['_a']['DATABASE_NAME']

        debug("t3 ODB: %s", settings.OTHER_DATABASES)
        debug("3 %s: start: default: %s", get_ident(), settings.DATABASE_NAME)
        debug("3 %s: start: conn: %s", get_ident(),
              connection.settings.DATABASE_NAME)
        
        debug("t3 waiting")
        EV.wait(2.0)
        func(*arg)
        debug("t3 complete")
    t3 = threading.Thread(target=start)
    t3.start()
    return t3

def debug(*arg):
    pass
#    msg, arg = arg[0], arg[1:]
#    print msg % arg

def start_response(code, headers):
    debug("start response: %s %s", code, headers)
    pass
    
class TestThreadIsolation(unittest.TestCase):
    # event used to synchronize threads so we can be sure they are running
    # together
    lock = threading.RLock()
    errors = []
    
    def setUp(self):
        debug("setup")
        self.settings = settings._target
        settings._target = UserSettingsHolder(copy.deepcopy(settings._target))
        settings.OTHER_DATABASES['_a']['MODELS'] =  ['ti.MX']
        settings.OTHER_DATABASES['_b']['MODELS'] = ['ti.MY']

        # normal settings holders aren't thread-safe, so we need to substitute
        # one that is (and so allows per-thread settings)
        holder = settings._target
        settings._target = LocalSettings(holder)

    def teardown(self):
        debug("teardown")
        settings._target = self.settings

    def add_thread_error(self, err):
        self.lock.acquire()
        try:
            self.errors.append(err)
        finally:
            self.lock.release()

    def thread_errors(self):
        self.lock.acquire()
        try:
            return self.errors[:]
        finally:
            self.lock.release()
            
    def request_one(self, path, request):
        """Start out with settings as originally configured"""
        from django.conf import settings
        debug("request_one: %s", settings.OTHER_DATABASES)

        self.assertEqual(model_connection_name(MQ), _default)
        self.assertEqual(model_connection_name(MX), '_a')
        self.assertEqual(
            MX._default_manager.db.connection.settings.DATABASE_NAME, 
            settings.OTHER_DATABASES['_a']['DATABASE_NAME'])
        self.assertEqual(model_connection_name(MY), '_b')
        self.assertEqual(
            MY._default_manager.db.connection.settings.DATABASE_NAME,
            settings.OTHER_DATABASES['_b']['DATABASE_NAME'])
        self.assert_(MQ._default_manager.db.connection is
                     connections[_default].connection)
        self.assertEqual(
            MQ._default_manager.db.connection.settings.DATABASE_NAME,
            settings.DATABASE_NAME)
        self.assertEqual(connection.settings.DATABASE_NAME,
                         settings.DATABASE_NAME)

    def request_two(self, path, request):
        """Between the first and second requests, settings change to assign
        model MY to a different connection
        """
        # from django.conf import settings
        debug("request_two: %s", settings.OTHER_DATABASES)

        try:
            self.assertEqual(model_connection_name(MQ), _default)
            self.assertEqual(model_connection_name(MX), '_a')
            self.assertEqual(
                MX._default_manager.db.connection.settings.DATABASE_NAME,
                settings.OTHER_DATABASES['_a']['DATABASE_NAME'])
            self.assertEqual(model_connection_name(MY), _default)
            self.assertEqual(
                MY._default_manager.db.connection.settings.DATABASE_NAME,
                settings.DATABASE_NAME)
            self.assert_(MQ._default_manager.db.connection is
                         connections[_default].connection)
            self.assertEqual(
                MQ._default_manager.db.connection.settings.DATABASE_NAME,
                settings.DATABASE_NAME)
            self.assertEqual(connection.settings.DATABASE_NAME,
                             settings.DATABASE_NAME)
        except:
            self.add_thread_error(sys.exc_info())

    def request_three(self, path, request):
        """Between the 2nd and 3rd requests, the settings at the names in
        OTHER_DATABASES have changed.
        """
        # from django.conf import settings
        debug("3 %s: %s", get_ident(), settings.OTHER_DATABASES)
        debug("3 %s: default: %s", get_ident(), settings.DATABASE_NAME)
        debug("3 %s: conn: %s", get_ident(),
              connection.settings.DATABASE_NAME)
        try:
            self.assertEqual(model_connection_name(MQ), _default)
            self.assertEqual(model_connection_name(MX), '_b')
            self.assertEqual(
                MX._default_manager.db.connection.settings.DATABASE_NAME,
                settings.OTHER_DATABASES['_b']['DATABASE_NAME'])
            self.assertEqual(model_connection_name(MY), '_a')
            self.assertEqual(
                MY._default_manager.db.connection.settings.DATABASE_NAME,
                settings.OTHER_DATABASES['_a']['DATABASE_NAME'])
            self.assert_(MQ._default_manager.db.connection is
                         connections[_default].connection)
            self.assertEqual(
                connection.settings.DATABASE_NAME,
                settings.OTHER_DATABASES['_a']['DATABASE_NAME'])
        except:
            self.add_thread_error(sys.exc_info())
        
    def test_thread_isolation(self):
        
        debug("running tests")

        env = os.environ.copy()
        env['PATH_INFO'] = '/'
        env['REQUEST_METHOD'] = 'GET'

        t2 = thread_two(MockHandler(self.request_two), env, start_response)
        t3 = thread_three(MockHandler(self.request_three), env, start_response)

        try:
            EV.set()
            MockHandler(self.request_one)(env, start_response)
        finally:
            t2.join()
            t3.join()
            err = self.thread_errors()
            if err:
                import traceback 
                for e in err:
                    traceback.print_exception(*e)
                    raise AssertionError("%s thread%s failed" %
                                         (len(err), len(err) > 1 and 's' or
                                          ''))
                
