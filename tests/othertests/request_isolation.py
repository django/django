# tests that db settings can change between requests
import copy
import os
from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler
from django.db import models, model_connection_name, _default, connection
from django.http import HttpResponse

# state holder
S = {}

# models
class MX(models.Model):
    val = models.CharField(maxlength=10)
    class Meta:
        app_label = 'ri'

        
class MY(models.Model):
    val = models.CharField(maxlength=10)
    class Meta:
        app_label = 'ri'


# tests
def test_one(path, request):
    """Start out with settings as originally configured"""
    assert model_connection_name(MX) == 'django_test_db_a'
    assert MX._default_manager.db.connection.settings.DATABASE_NAME == \
           settings.OTHER_DATABASES['django_test_db_a']['DATABASE_NAME']
    assert model_connection_name(MY) == 'django_test_db_b'
    assert MY._default_manager.db.connection.settings.DATABASE_NAME == \
           settings.OTHER_DATABASES['django_test_db_b']['DATABASE_NAME'], \
           "%s != %s" % \
           (MY._default_manager.db.connection.settings.DATABASE_NAME,
            settings.OTHER_DATABASES['django_test_db_b']['DATABASE_NAME'])


def test_two(path, request):
    """Between the first and second requests, settings change to assign
    model MY to a different connection
    """
    assert model_connection_name(MX) == 'django_test_db_a'
    assert MX._default_manager.db.connection.settings.DATABASE_NAME == \
           settings.OTHER_DATABASES['django_test_db_a']['DATABASE_NAME']
    assert model_connection_name(MY) == _default
    assert MY._default_manager.db.connection.settings.DATABASE_NAME == \
           settings.DATABASE_NAME, "%s != %s" % \
           (MY._default_manager.db.connection.settings.DATABASE_NAME,
            settings.DATABASE_NAME)


def test_three(path, request):
    """Between the 2nd and 3rd requests, the settings at the names in
    OTHER_DATABASES have changed.
    """
    assert model_connection_name(MX) == 'django_test_db_b'
    assert MX._default_manager.db.connection.settings.DATABASE_NAME == \
           settings.OTHER_DATABASES['django_test_db_b']['DATABASE_NAME']
    assert model_connection_name(MY) == 'django_test_db_a'
    assert MY._default_manager.db.connection.settings.DATABASE_NAME == \
           settings.OTHER_DATABASES['django_test_db_a']['DATABASE_NAME'], \
           "%s != %s" % \
           (MY._default_manager.db.connection.settings.DATABASE_NAME,
            settings.OTHER_DATABASES['django_test_db_a']['DATABASE_NAME'])


# helpers
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
    S['ODB'] = copy.deepcopy(settings.OTHER_DATABASES)
    for sk in [ k for k in dir(settings) if k.startswith('DATABASE') ]:
        S[sk] = getattr(settings, sk)
    
    settings.OTHER_DATABASES['django_test_db_a']['MODELS'] = ['ri.MX']
    settings.OTHER_DATABASES['django_test_db_b']['MODELS'] = ['ri.MY']


def teardown():
    debug("teardown")
    settings.OTHER_DATABASES = S['ODB']
    for sk in [ k for k in S.keys() if k.startswith('DATABASE') ]:
        setattr(settings, sk, S[sk])


def start_response(code, headers):
    debug("start response: %s %s", code, headers)
    pass


def main():
    debug("running tests")

    env = os.environ.copy()
    env['PATH_INFO'] = '/'
    env['REQUEST_METHOD'] = 'GET'
    
    MockHandler(test_one)(env, start_response)
    
    settings.OTHER_DATABASES['django_test_db_b']['MODELS'] = []
    MockHandler(test_two)(env, start_response)
    
    settings.OTHER_DATABASES['django_test_db_b']['MODELS'] = ['ri.MY']
    settings.OTHER_DATABASES['django_test_db_b'], \
        settings.OTHER_DATABASES['django_test_db_a'] = \
        settings.OTHER_DATABASES['django_test_db_a'], \
        settings.OTHER_DATABASES['django_test_db_b']
    MockHandler(test_three)(env, start_response)

    
def run_tests(verbosity=0):
    S['verbosity'] = verbosity
    setup()
    try:
        main()
    finally:
        teardown()

        
if __name__ == '__main__':
    run_tests(2)
