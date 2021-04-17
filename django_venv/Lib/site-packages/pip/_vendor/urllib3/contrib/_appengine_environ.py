"""
This module provides means to detect the App Engine environment.
"""

import os


def is_appengine():
    return (is_local_appengine() or
            is_prod_appengine() or
            is_prod_appengine_mvms())


def is_appengine_sandbox():
    return is_appengine() and not is_prod_appengine_mvms()


def is_local_appengine():
    return ('APPENGINE_RUNTIME' in os.environ and
            'Development/' in os.environ['SERVER_SOFTWARE'])


def is_prod_appengine():
    return ('APPENGINE_RUNTIME' in os.environ and
            'Google App Engine/' in os.environ['SERVER_SOFTWARE'] and
            not is_prod_appengine_mvms())


def is_prod_appengine_mvms():
    return os.environ.get('GAE_VM', False) == 'true'
