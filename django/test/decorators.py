from django.core import urlresolvers
from django.test import SkippedTest

def views_required(required_views=[]):
    def urls_found():
        try:
            for view in required_views:
                urlresolvers.reverse(view)
            return True
        except urlresolvers.NoReverseMatch:
            return False
    reason = 'Required view%s for this test not found: %s' % \
            (len(required_views) > 1 and 's' or '', ', '.join(required_views))
    return conditional_skip(urls_found, reason=reason)

def modules_required(required_modules=[]):
    def modules_found():
        try:
            for module in required_modules:
                __import__(module)
            return True
        except ImportError:
            return False
    reason = 'Required module%s for this test not found: %s' % \
            (len(required_modules) > 1 and 's' or '', ', '.join(required_modules))
    return conditional_skip(modules_found, reason=reason)

def skip_specific_database(database_engine):
    def database_check():
        from django.conf import settings
        return database_engine == settings.DATABASE_ENGINE
    reason = 'Test not run for database engine %s.' % database_engine
    return conditional_skip(database_check, reason=reason)

def conditional_skip(required_condition, reason=''):
    if required_condition():
        return lambda x: x
    else:
        return skip_test(reason)

def skip_test(reason=''):
    def _skip(x):
        raise SkippedTest(reason=reason)
    return lambda x: _skip
