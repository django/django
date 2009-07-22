"""

This code is originally by miracle2k:
http://bitbucket.org/miracle2k/djutils/src/97f92c32c621/djutils/test/twill.py


Integrates the twill web browsing scripting language with Django.

Provides too main functions, ``setup()`` and ``teardown``, that hook
(and unhook) a certain host name to the WSGI interface of your Django
app, making it possible to test your site using twill without actually
going through TCP/IP.

It also changes the twill browsing behaviour, so that relative urls
per default point to the intercept (e.g. your Django app), so long
as you don't browse away from that host. Further, you are allowed to
specify the target url as arguments to Django's ``reverse()``.

Usage:

    from test_utils.utils import twill_runner as twill
    twill.setup()
    try:
        twill.go('/')                     # --> Django WSGI
        twill.code(200)

        twill.go('http://google.com')
        twill.go('/services')             # --> http://google.com/services

        twill.go('/list', default=True)   # --> back to Django WSGI

        twill.go('proj.app.views.func',
                 args=[1,2,3])
    finally:
        twill.teardown()

For more information about twill, see:
    http://twill.idyll.org/
"""

# allows us to import global twill as opposed to this module
from __future__ import absolute_import

# TODO: import all names with a _-prefix to keep the namespace clean with the twill stuff?
import urlparse
import cookielib

import twill
import twill.commands
import twill.browser

from django.conf import settings
from django.core.servers.basehttp import AdminMediaHandler
from django.core.handlers.wsgi import WSGIHandler
from django.core.urlresolvers import reverse
from django.http import HttpRequest
from django.utils.datastructures import SortedDict
from django.contrib import auth

from django.core.management.commands.test_windmill import ServerContainer, attempt_import

# make available through this module
from twill.commands import *

__all__ = ('INSTALLED', 'setup', 'teardown', 'reverse',) + tuple(twill.commands.__all__)


DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 9090
INSTALLED = SortedDict()   # keep track of the installed hooks


def setup(host=None, port=None, allow_xhtml=True, propagate=True):
    """Install the WSGI hook for ``host`` and ``port``.

    The default values will be used if host or port are not specified.

    ``allow_xhtml`` enables a workaround for the "not viewer HTML"
    error when browsing sites that are determined to be XHTML, e.g.
    featuring xhtml-ish mimetypes.

    Unless ``propagate specifies otherwise``, the
    ``DEBUG_PROPAGATE_EXCEPTIONS`` will be enabled for better debugging:
    when using twill, we don't really want to see 500 error pages,
    but rather directly the exceptions that occured on the view side.

    Multiple calls to this function will only result in one handler
    for each host/port combination being installed.
    """

    host = host or DEFAULT_HOST
    port = port or DEFAULT_PORT
    key = (host, port)

    if not key in INSTALLED:
        # installer wsgi handler
        app = AdminMediaHandler(WSGIHandler())
        twill.add_wsgi_intercept(host, port, lambda: app)

        # start browser fresh
        browser = get_browser()
        browser.diverged = False

        # enable xhtml mode if requested
        _enable_xhtml(browser, allow_xhtml)

        # init debug propagate setting, and remember old value
        if propagate:
            old_propgate_setting = settings.DEBUG_PROPAGATE_EXCEPTIONS
            settings.DEBUG_PROPAGATE_EXCEPTIONS = True
        else:
            old_propgate_setting = None

        INSTALLED[key] = (app, old_propgate_setting)
        return browser
    return False


def teardown(host=None, port=None):
    """Remove an installed WSGI hook for ``host`` and ```port``.

    If no host or port is passed, the default values will be assumed.
    If no hook is installed for the defaults, and both the host and
    port are missing, the last hook installed will be removed.

    Returns True if a hook was removed, otherwise False.
    """

    both_missing = not host and not port
    host = host or DEFAULT_HOST
    port = port or DEFAULT_PORT
    key = (host, port)

    key_to_delete = None
    if key in INSTALLED:
        key_to_delete = key
    if not key in INSTALLED and both_missing and len(INSTALLED) > 0:
        host, port = key_to_delete = INSTALLED.keys()[-1]

    if key_to_delete:
        _, old_propagate = INSTALLED[key_to_delete]
        del INSTALLED[key_to_delete]
        result = True
        if old_propagate is not None:
            settings.DEBUG_PROPAGATE_EXCEPTIONS = old_propagate
    else:
        result = False

    # note that our return value is just a guess according to our
    # own records, we pass the request on to twill in any case
    twill.remove_wsgi_intercept(host, port)
    return result


def _enable_xhtml(browser, enable):
    """Twill (darcs from 19-09-2008) does not work with documents
    identifying themselves as XHTML.

    This is a workaround.
    """
    factory = browser._browser._factory
    factory.basic_factory._response_type_finder._allow_xhtml = \
        factory.soup_factory._response_type_finder._allow_xhtml = \
            enable


class _EasyTwillBrowser(twill.browser.TwillBrowser):
    """Custom version of twill's browser class that defaults relative
    URLs to the last installed hook, if available.

    It also supports reverse resolving, and some additional commands.
    """

    def __init__(self, *args, **kwargs):
        self.diverged = False
        self._testing_ = False
        super(_EasyTwillBrowser, self).__init__(*args, **kwargs)

    def go(self, url, args=None, kwargs=None, default=None):
        assert not ((args or kwargs) and default==False)

        if args or kwargs:
            url = reverse(url, args=args, kwargs=kwargs)
            default = True    # default is implied

        if INSTALLED:
            netloc = '%s:%s' % INSTALLED.keys()[-1]
            urlbits = urlparse.urlsplit(url)
            if not urlbits[0]:
                if default:
                    # force "undiverge"
                    self.diverged = False
                if not self.diverged:
                    url = urlparse.urlunsplit(('http', netloc)+urlbits[2:])
            else:
                self.diverged = True

        if self._testing_:   # hack that makes it simple for us to test this
            return url
        return super(_EasyTwillBrowser, self).go(url)

    def login(self, **credentials):
        """Log the user with the given credentials into your Django
        site.

        To further simplify things, rather than giving the credentials,
        you may pass a ``user`` parameter with the ``User`` instance you
        want to login. Note that in this case the user will not be
        further validated, i.e. it is possible to login an inactive user
        this way.

        This works regardless of the url currently browsed, but does
        require the WSGI intercept to be setup.

        Returns ``True`` if login was possible; ``False`` if the
        provided credentials are incorrect, or the user is inactive,
        or if the sessions framework is not available.

        Based on ``django.test.client.Client.logout``.

        Note: A ``twill.reload()`` will not refresh the cookies sent
        with the request, so your login will not have any effect there.
        This is different for ``logout``, since it actually invalidates
        the session server-side, thus making the current key invalid.
        """

        if not 'django.contrib.sessions' in settings.INSTALLED_APPS:
            return False

        host, port = INSTALLED.keys()[-1]

        # determine the user we want to login
        user = credentials.pop('user', None)
        if user:
            # Login expects the user object to reference it's backend.
            # Since we're not going through ``authenticate``, we'll
            # have to do this ourselves.
            backend = auth.get_backends()[0]
            user.backend = user.backend = "%s.%s" % (
                backend.__module__, backend.__class__.__name__)
        else:
            user = auth.authenticate(**credentials)
            if not user or not user.is_active:
                return False

        # create a fake request to use with ``auth.login``
        request = HttpRequest()
        request.session = __import__(settings.SESSION_ENGINE, {}, {}, ['']).SessionStore()
        auth.login(request, user)
        request.session.save()

        # set the cookie to represent the session
        self.cj.set_cookie(cookielib.Cookie(
            version=None,
            name=settings.SESSION_COOKIE_NAME,
            value=request.session.session_key,
            port=str(port),   # must be a string
            port_specified = False,
            domain=host, #settings.SESSION_COOKIE_DOMAIN,
            domain_specified=True,
            domain_initial_dot=False,
            path='/',
            path_specified=True,
            secure=settings.SESSION_COOKIE_SECURE or None,
            expires=None,
            discard=None,
            comment=None,
            comment_url=None,
            rest=None
        ))

        return True

    def logout(self):
        """Log the current user out of your Django site.

        This works regardless of the url currently browsed, but does
        require the WSGI intercept to be setup.

        Based on ``django.test.client.Client.logout``.
        """
        host, port = INSTALLED.keys()[-1]
        for cookie in self.cj:
            if cookie.name == settings.SESSION_COOKIE_NAME \
                    and cookie.domain==host \
                    and (not cookie.port or str(cookie.port)==str(port)):
                session = __import__(settings.SESSION_ENGINE, {}, {}, ['']).SessionStore()
                session.delete(session_key=cookie.value)
                self.cj.clear(cookie.domain, cookie.path, cookie.name)
                return True
        return False


def go(*args, **kwargs):
    # replace the default ``go`` to make the additional
    # arguments that our custom browser provides available.
    browser = get_browser()
    browser.go(*args, **kwargs)
    return browser.get_url()

def login(*args, **kwargs):
    return get_browser().login(*args, **kwargs)

def logout(*args, **kwargs):
    return get_browser().logout(*args, **kwargs)

def reset_browser(*args, **kwargs):
    # replace the default ``reset_browser`` to ensure
    # that our custom browser class is used
    result = twill.commands.reset_browser(*args, **kwargs)
    twill.commands.browser = _EasyTwillBrowser()
    return result

# Monkey-patch our custom browser into twill; this will be global, but
# will only have an actual effect when intercepts are installed through
# our module (via ``setup``).
# Unfortunately, twill pretty much forces us to use the same global
# state it does itself, lest us reimplement everything from
# ``twill.commands``. It's a bit of a shame, we could provide dedicated
# browser instances for each call to ``setup()``.
reset_browser()


def url(should_be=None):
    """Like the default ``url()``, but can be called without arguments,
    in which case it returns the current url.
    """

    if should_be is None:
        return get_browser().get_url()
    else:
        return twill.commands.url(should_be)
