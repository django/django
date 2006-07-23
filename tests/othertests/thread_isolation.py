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
from thread import get_ident

from django.conf import settings, UserSettingsHolder
from django.core.handlers.wsgi import WSGIHandler
from django.db import models, model_connection_name, _default, connection, \
     connections
from django.http import HttpResponse

try:
    # Only exists in Python 2.4+
    from threading import local
except ImportError:
    # Import copy of _thread_local.py from Python 2.4
    from django.utils._threading_local import local

# state holder
S = {}

# models
class MQ(models.Model):
    val = models.CharField(maxlength=10)
    class Meta:
        app_label = 'ti'


class MX(models.Model):
    val = models.CharField(maxlength=10)
    class Meta:
        app_label = 'ti'

        
class MY(models.Model):
    val = models.CharField(maxlength=10)
    class Meta:
        app_label = 'ti'

# eventused to synchronize threads so we can be sure they are running
# together
ev = threading.Event()


def test_one(path, request):
    """Start out with settings as originally configured"""
    from django.conf import settings
    debug("test_one: %s", settings.OTHER_DATABASES)

    assert model_connection_name(MQ) == _default
    assert model_connection_name(MX) == 'django_test_db_a', \
           "%s != 'django_test_db_a'" % model_connection_name(MX)
    assert MX._default_manager.db.connection.settings.DATABASE_NAME == \
           settings.OTHER_DATABASES['django_test_db_a']['DATABASE_NAME']
    assert model_connection_name(MY) == 'django_test_db_b'
    assert MY._default_manager.db.connection.settings.DATABASE_NAME == \
           settings.OTHER_DATABASES['django_test_db_b']['DATABASE_NAME'], \
           "%s != %s" % \
           (MY._default_manager.db.connection.settings.DATABASE_NAME,
            settings.OTHER_DATABASES['django_test_db_b']['DATABASE_NAME'])
    assert MQ._default_manager.db.connection is \
           connections[_default].connection        
    assert MQ._default_manager.db.connection.settings.DATABASE_NAME == \
           settings.DATABASE_NAME
    assert connection.settings.DATABASE_NAME ==  settings.DATABASE_NAME


def test_two(path, request):
    """Between the first and second requests, settings change to assign
    model MY to a different connection
    """
    # from django.conf import settings
    debug("test_two: %s", settings.OTHER_DATABASES)

    try:
        assert model_connection_name(MQ) == _default
        assert model_connection_name(MX) == 'django_test_db_a'
        assert MX._default_manager.db.connection.settings.DATABASE_NAME == \
               settings.OTHER_DATABASES['django_test_db_a']['DATABASE_NAME']
        assert model_connection_name(MY) == _default
        assert MY._default_manager.db.connection.settings.DATABASE_NAME == \
               settings.DATABASE_NAME, "%s != %s" % \
               (MY._default_manager.db.connection.settings.DATABASE_NAME,
                settings.DATABASE_NAME)
        assert MQ._default_manager.db.connection is \
           connections[_default].connection        
        assert MQ._default_manager.db.connection.settings.DATABASE_NAME == \
               settings.DATABASE_NAME
        assert connection.settings.DATABASE_NAME == settings.DATABASE_NAME
    except:
        S.setdefault('errors',[]).append(sys.exc_info())


def test_three(path, request):
    """Between the 2nd and 3rd requests, the settings at the names in
    OTHER_DATABASES have changed.
    """
    # from django.conf import settings
    debug("3 %s: %s", get_ident(), settings.OTHER_DATABASES)
    debug("3 %s: default: %s", get_ident(), settings.DATABASE_NAME)
    debug("3 %s: conn: %s", get_ident(), connection.settings.DATABASE_NAME)
    
    try:
        assert model_connection_name(MQ) == _default
        assert model_connection_name(MX) == 'django_test_db_b'
        assert MX._default_manager.db.connection.settings.DATABASE_NAME == \
               settings.OTHER_DATABASES['django_test_db_b']['DATABASE_NAME'],\
               "%s != %s" % \
               (MX._default_manager.db.connection.settings.DATABASE_NAME,
                settings.OTHER_DATABASES['django_test_db_b']['DATABASE_NAME'])
        assert model_connection_name(MY) == 'django_test_db_a'
        assert MY._default_manager.db.connection.settings.DATABASE_NAME == \
               settings.OTHER_DATABASES['django_test_db_a']['DATABASE_NAME'],\
               "%s != %s" % \
               (MY._default_manager.db.connection.settings.DATABASE_NAME,
                settings.OTHER_DATABASES['django_test_db_a']['DATABASE_NAME'])
        assert MQ._default_manager.db.connection is \
           connections[_default].connection
        assert connection.settings.DATABASE_NAME == \
               settings.OTHER_DATABASES['django_test_db_a']['DATABASE_NAME'],\
               "%s != %s" % \
               (connection.settings.DATABASE_NAME,
                settings.OTHER_DATABASES['django_test_db_a']['DATABASE_NAME'])
    except:
        S.setdefault('errors',[]).append(sys.exc_info())
        
    

# helpers
def thread_two(func, *arg):
    def start():
        # from django.conf import settings
        settings.OTHER_DATABASES['django_test_db_b']['MODELS'] = []

        debug("t2 ODB: %s", settings.OTHER_DATABASES)
        debug("t2 waiting")
        ev.wait(2.0)
        func(*arg)
        debug("t2 complete")
    t2 = threading.Thread(target=start)
    t2.start()
    return t2


def thread_three(func, *arg):
    def start():
        # from django.conf import settings            
        settings.OTHER_DATABASES['django_test_db_b']['MODELS'] = ['ti.MY']
        settings.OTHER_DATABASES['django_test_db_b'], \
            settings.OTHER_DATABASES['django_test_db_a'] = \
            settings.OTHER_DATABASES['django_test_db_a'], \
            settings.OTHER_DATABASES['django_test_db_b']

        settings.DATABASE_NAME = \
            settings.OTHER_DATABASES['django_test_db_a']['DATABASE_NAME']

        debug("t3 ODB: %s", settings.OTHER_DATABASES)
        debug("3 %s: start: default: %s", get_ident(), settings.DATABASE_NAME)
        debug("3 %s: start: conn: %s", get_ident(),
              connection.settings.DATABASE_NAME)
        
        debug("t3 waiting")
        ev.wait(2.0)
        func(*arg)
        debug("t3 complete")
    t3 = threading.Thread(target=start)
    t3.start()
    return t3
    
# helpers
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
        
class MockHandler(WSGIHandler):

    def __init__(self, test):
        self.test = test
        super(MockHandler, self).__init__()
        
    def get_response(self, path, request):
        # debug("mock handler answering %s, %s", path, request)
        return HttpResponse(self.test(path, request))
        

def pr(*arg):
    if S['verbosity'] >= 1:
        msg, arg = arg[0], arg[1:]
        print msg % arg


def debug(*arg):
    if S['verbosity'] >= 2:
        msg, arg = arg[0], arg[1:]
        print msg % arg


def setup():
    debug("setup")
    S['settings'] = settings._target
    settings._target = UserSettingsHolder(copy.deepcopy(settings._target))    
    settings.OTHER_DATABASES['django_test_db_a']['MODELS'] =  ['ti.MX']
    settings.OTHER_DATABASES['django_test_db_b']['MODELS'] = ['ti.MY']

    # normal settings holders aren't thread-safe, so we need to substitute
    # one that is (and so allows per-thread settings)
    holder = settings._target
    settings._target = LocalSettings(holder)
    
    
def teardown():
    debug("teardown")
    settings._target = S['settings']


def start_response(code, headers):
    debug("start response: %s %s", code, headers)
    pass


def main():
    debug("running tests")

    env = os.environ.copy()
    env['PATH_INFO'] = '/'
    env['REQUEST_METHOD'] = 'GET'
    
    t2 = thread_two(MockHandler(test_two), env, start_response)
    t3 = thread_three(MockHandler(test_three), env, start_response)
    
    try:
        ev.set()
        MockHandler(test_one)(env, start_response)
    finally:
        t2.join()
        t3.join()
        err = S.get('errors', [])
        if err:
            import traceback        
            for e in err:
                traceback.print_exception(*e)
                raise AssertionError("%s thread%s failed" %
                                     (len(err), len(err) > 1 and 's' or ''))
    
def run_tests(verbosity=0):
    S['verbosity'] = verbosity
    
    setup()
    try:
        main()
    finally:
        teardown()

        
if __name__ == '__main__':
    from django.conf import settings
    
    settings.DATABASE_NAME = ':memory:'
    print "MAIN start! ", connection.settings.DATABASE_NAME
    connection.cursor()
    run_tests(2)
