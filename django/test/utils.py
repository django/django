import logging
import re
import sys
import time
import warnings
from contextlib import contextmanager
from functools import wraps
from unittest import skipIf, skipUnless
from xml.dom.minidom import Node, parseString

from django.apps import apps
from django.conf import UserSettingsHolder, settings
from django.core import mail
from django.core.signals import request_started
from django.core.urlresolvers import get_script_prefix, set_script_prefix
from django.db import reset_queries
from django.http import request
from django.template import Template
from django.test.signals import setting_changed, template_rendered
from django.utils import six
from django.utils.decorators import ContextDecorator
from django.utils.encoding import force_str
from django.utils.translation import deactivate

try:
    import jinja2
except ImportError:
    jinja2 = None


__all__ = (
    'Approximate', 'ContextList', 'isolate_lru_cache', 'get_runner',
    'modify_settings', 'override_settings',
    'requires_tz_support',
    'setup_test_environment', 'teardown_test_environment',
)

TZ_SUPPORT = hasattr(time, 'tzset')


class Approximate(object):
    def __init__(self, val, places=7):
        self.val = val
        self.places = places

    def __repr__(self):
        return repr(self.val)

    def __eq__(self, other):
        if self.val == other:
            return True
        return round(abs(self.val - other), self.places) == 0


class ContextList(list):
    """A wrapper that provides direct key access to context items contained
    in a list of context objects.
    """
    def __getitem__(self, key):
        if isinstance(key, six.string_types):
            for subcontext in self:
                if key in subcontext:
                    return subcontext[key]
            raise KeyError(key)
        else:
            return super(ContextList, self).__getitem__(key)

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        return True

    def keys(self):
        """
        Flattened keys of subcontexts.
        """
        keys = set()
        for subcontext in self:
            for dict in subcontext:
                keys |= set(dict.keys())
        return keys


def instrumented_test_render(self, context):
    """
    An instrumented Template render method, providing a signal
    that can be intercepted by the test system Client
    """
    template_rendered.send(sender=self, template=self, context=context)
    return self.nodelist.render(context)


def setup_test_environment():
    """Perform any global pre-test setup. This involves:

        - Installing the instrumented test renderer
        - Set the email backend to the locmem email backend.
        - Setting the active locale to match the LANGUAGE_CODE setting.
    """
    Template._original_render = Template._render
    Template._render = instrumented_test_render

    # Storing previous values in the settings module itself is problematic.
    # Store them in arbitrary (but related) modules instead. See #20636.

    mail._original_email_backend = settings.EMAIL_BACKEND
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

    request._original_allowed_hosts = settings.ALLOWED_HOSTS
    settings.ALLOWED_HOSTS = ['*']

    mail.outbox = []

    deactivate()


def teardown_test_environment():
    """Perform any global post-test teardown. This involves:

        - Restoring the original test renderer
        - Restoring the email sending functions
    """
    Template._render = Template._original_render
    del Template._original_render

    settings.EMAIL_BACKEND = mail._original_email_backend
    del mail._original_email_backend

    settings.ALLOWED_HOSTS = request._original_allowed_hosts
    del request._original_allowed_hosts

    del mail.outbox


def get_runner(settings, test_runner_class=None):
    if not test_runner_class:
        test_runner_class = settings.TEST_RUNNER

    test_path = test_runner_class.split('.')
    # Allow for Python 2.5 relative paths
    if len(test_path) > 1:
        test_module_name = '.'.join(test_path[:-1])
    else:
        test_module_name = '.'
    test_module = __import__(test_module_name, {}, {}, force_str(test_path[-1]))
    test_runner = getattr(test_module, test_path[-1])
    return test_runner


class override_settings(object):
    """
    Acts as either a decorator, or a context manager. If it's a decorator it
    takes a function and returns a wrapped function. If it's a contextmanager
    it's used with the ``with`` statement. In either event entering/exiting
    are called before and after, respectively, the function/block is executed.
    """
    def __init__(self, **kwargs):
        self.options = kwargs

    def __enter__(self):
        self.enable()

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable()

    def __call__(self, test_func):
        from django.test import SimpleTestCase
        if isinstance(test_func, type):
            if not issubclass(test_func, SimpleTestCase):
                raise Exception(
                    "Only subclasses of Django SimpleTestCase can be decorated "
                    "with override_settings")
            self.save_options(test_func)
            return test_func
        else:
            @wraps(test_func)
            def inner(*args, **kwargs):
                with self:
                    return test_func(*args, **kwargs)
        return inner

    def save_options(self, test_func):
        if test_func._overridden_settings is None:
            test_func._overridden_settings = self.options
        else:
            # Duplicate dict to prevent subclasses from altering their parent.
            test_func._overridden_settings = dict(
                test_func._overridden_settings, **self.options)

    def enable(self):
        # Keep this code at the beginning to leave the settings unchanged
        # in case it raises an exception because INSTALLED_APPS is invalid.
        if 'INSTALLED_APPS' in self.options:
            try:
                apps.set_installed_apps(self.options['INSTALLED_APPS'])
            except Exception:
                apps.unset_installed_apps()
                raise
        override = UserSettingsHolder(settings._wrapped)
        for key, new_value in self.options.items():
            setattr(override, key, new_value)
        self.wrapped = settings._wrapped
        settings._wrapped = override
        for key, new_value in self.options.items():
            setting_changed.send(sender=settings._wrapped.__class__,
                                 setting=key, value=new_value, enter=True)

    def disable(self):
        if 'INSTALLED_APPS' in self.options:
            apps.unset_installed_apps()
        settings._wrapped = self.wrapped
        del self.wrapped
        for key in self.options:
            new_value = getattr(settings, key, None)
            setting_changed.send(sender=settings._wrapped.__class__,
                                 setting=key, value=new_value, enter=False)


class modify_settings(override_settings):
    """
    Like override_settings, but makes it possible to append, prepend or remove
    items instead of redefining the entire list.
    """
    def __init__(self, *args, **kwargs):
        if args:
            # Hack used when instantiating from SimpleTestCase.setUpClass.
            assert not kwargs
            self.operations = args[0]
        else:
            assert not args
            self.operations = list(kwargs.items())

    def save_options(self, test_func):
        if test_func._modified_settings is None:
            test_func._modified_settings = self.operations
        else:
            # Duplicate list to prevent subclasses from altering their parent.
            test_func._modified_settings = list(
                test_func._modified_settings) + self.operations

    def enable(self):
        self.options = {}
        for name, operations in self.operations:
            try:
                # When called from SimpleTestCase.setUpClass, values may be
                # overridden several times; cumulate changes.
                value = self.options[name]
            except KeyError:
                value = list(getattr(settings, name, []))
            for action, items in operations.items():
                # items my be a single value or an iterable.
                if isinstance(items, six.string_types):
                    items = [items]
                if action == 'append':
                    value = value + [item for item in items if item not in value]
                elif action == 'prepend':
                    value = [item for item in items if item not in value] + value
                elif action == 'remove':
                    value = [item for item in value if item not in items]
                else:
                    raise ValueError("Unsupported action: %s" % action)
            self.options[name] = value
        super(modify_settings, self).enable()


def override_system_checks(new_checks, deployment_checks=None):
    """ Acts as a decorator. Overrides list of registered system checks.
    Useful when you override `INSTALLED_APPS`, e.g. if you exclude `auth` app,
    you also need to exclude its system checks. """

    from django.core.checks.registry import registry

    def outer(test_func):
        @wraps(test_func)
        def inner(*args, **kwargs):
            old_checks = registry.registered_checks
            registry.registered_checks = new_checks
            old_deployment_checks = registry.deployment_checks
            if deployment_checks is not None:
                registry.deployment_checks = deployment_checks
            try:
                return test_func(*args, **kwargs)
            finally:
                registry.registered_checks = old_checks
                registry.deployment_checks = old_deployment_checks
        return inner
    return outer


def compare_xml(want, got):
    """Tries to do a 'xml-comparison' of want and got.  Plain string
    comparison doesn't always work because, for example, attribute
    ordering should not be important. Comment nodes are not considered in the
    comparison.

    Based on http://codespeak.net/svn/lxml/trunk/src/lxml/doctestcompare.py
    """
    _norm_whitespace_re = re.compile(r'[ \t\n][ \t\n]+')

    def norm_whitespace(v):
        return _norm_whitespace_re.sub(' ', v)

    def child_text(element):
        return ''.join(c.data for c in element.childNodes
                       if c.nodeType == Node.TEXT_NODE)

    def children(element):
        return [c for c in element.childNodes
                if c.nodeType == Node.ELEMENT_NODE]

    def norm_child_text(element):
        return norm_whitespace(child_text(element))

    def attrs_dict(element):
        return dict(element.attributes.items())

    def check_element(want_element, got_element):
        if want_element.tagName != got_element.tagName:
            return False
        if norm_child_text(want_element) != norm_child_text(got_element):
            return False
        if attrs_dict(want_element) != attrs_dict(got_element):
            return False
        want_children = children(want_element)
        got_children = children(got_element)
        if len(want_children) != len(got_children):
            return False
        for want, got in zip(want_children, got_children):
            if not check_element(want, got):
                return False
        return True

    def first_node(document):
        for node in document.childNodes:
            if node.nodeType != Node.COMMENT_NODE:
                return node

    want, got = strip_quotes(want, got)
    want = want.replace('\\n', '\n')
    got = got.replace('\\n', '\n')

    # If the string is not a complete xml document, we may need to add a
    # root element. This allow us to compare fragments, like "<foo/><bar/>"
    if not want.startswith('<?xml'):
        wrapper = '<root>%s</root>'
        want = wrapper % want
        got = wrapper % got

    # Parse the want and got strings, and compare the parsings.
    want_root = first_node(parseString(want))
    got_root = first_node(parseString(got))

    return check_element(want_root, got_root)


def strip_quotes(want, got):
    """
    Strip quotes of doctests output values:

    >>> strip_quotes("'foo'")
    "foo"
    >>> strip_quotes('"foo"')
    "foo"
    """
    def is_quoted_string(s):
        s = s.strip()
        return (len(s) >= 2
                and s[0] == s[-1]
                and s[0] in ('"', "'"))

    def is_quoted_unicode(s):
        s = s.strip()
        return (len(s) >= 3
                and s[0] == 'u'
                and s[1] == s[-1]
                and s[1] in ('"', "'"))

    if is_quoted_string(want) and is_quoted_string(got):
        want = want.strip()[1:-1]
        got = got.strip()[1:-1]
    elif is_quoted_unicode(want) and is_quoted_unicode(got):
        want = want.strip()[2:-1]
        got = got.strip()[2:-1]
    return want, got


def str_prefix(s):
    return s % {'_': '' if six.PY3 else 'u'}


class CaptureQueriesContext(object):
    """
    Context manager that captures queries executed by the specified connection.
    """
    def __init__(self, connection):
        self.connection = connection

    def __iter__(self):
        return iter(self.captured_queries)

    def __getitem__(self, index):
        return self.captured_queries[index]

    def __len__(self):
        return len(self.captured_queries)

    @property
    def captured_queries(self):
        return self.connection.queries[self.initial_queries:self.final_queries]

    def __enter__(self):
        self.force_debug_cursor = self.connection.force_debug_cursor
        self.connection.force_debug_cursor = True
        self.initial_queries = len(self.connection.queries_log)
        self.final_queries = None
        request_started.disconnect(reset_queries)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.force_debug_cursor = self.force_debug_cursor
        request_started.connect(reset_queries)
        if exc_type is not None:
            return
        self.final_queries = len(self.connection.queries_log)


class ignore_warnings(object):
    def __init__(self, **kwargs):
        self.ignore_kwargs = kwargs
        if 'message' in self.ignore_kwargs or 'module' in self.ignore_kwargs:
            self.filter_func = warnings.filterwarnings
        else:
            self.filter_func = warnings.simplefilter

    def __call__(self, decorated):
        if isinstance(decorated, type):
            # A class is decorated
            saved_setUp = decorated.setUp
            saved_tearDown = decorated.tearDown

            def setUp(inner_self):
                self.catch_warnings = warnings.catch_warnings()
                self.catch_warnings.__enter__()
                self.filter_func('ignore', **self.ignore_kwargs)
                saved_setUp(inner_self)

            def tearDown(inner_self):
                saved_tearDown(inner_self)
                self.catch_warnings.__exit__(*sys.exc_info())

            decorated.setUp = setUp
            decorated.tearDown = tearDown
            return decorated
        else:
            @wraps(decorated)
            def inner(*args, **kwargs):
                with warnings.catch_warnings():
                    self.filter_func('ignore', **self.ignore_kwargs)
                    return decorated(*args, **kwargs)
            return inner


@contextmanager
def patch_logger(logger_name, log_level):
    """
    Context manager that takes a named logger and the logging level
    and provides a simple mock-like list of messages received
    """
    calls = []

    def replacement(msg, *args, **kwargs):
        calls.append(msg % args)
    logger = logging.getLogger(logger_name)
    orig = getattr(logger, log_level)
    setattr(logger, log_level, replacement)
    try:
        yield calls
    finally:
        setattr(logger, log_level, orig)


# On OSes that don't provide tzset (Windows), we can't set the timezone
# in which the program runs. As a consequence, we must skip tests that
# don't enforce a specific timezone (with timezone.override or equivalent),
# or attempt to interpret naive datetimes in the default timezone.

requires_tz_support = skipUnless(TZ_SUPPORT,
        "This test relies on the ability to run a program in an arbitrary "
        "time zone, but your operating system isn't able to do that.")


@contextmanager
def extend_sys_path(*paths):
    """Context manager to temporarily add paths to sys.path."""
    _orig_sys_path = sys.path[:]
    sys.path.extend(paths)
    try:
        yield
    finally:
        sys.path = _orig_sys_path


@contextmanager
def isolate_lru_cache(lru_cache_object):
    """Clear the cache of an LRU cache object on entering and exiting."""
    lru_cache_object.cache_clear()
    try:
        yield
    finally:
        lru_cache_object.cache_clear()


@contextmanager
def captured_output(stream_name):
    """Return a context manager used by captured_stdout/stdin/stderr
    that temporarily replaces the sys stream *stream_name* with a StringIO.

    Note: This function and the following ``captured_std*`` are copied
          from CPython's ``test.support`` module."""
    orig_stdout = getattr(sys, stream_name)
    setattr(sys, stream_name, six.StringIO())
    try:
        yield getattr(sys, stream_name)
    finally:
        setattr(sys, stream_name, orig_stdout)


def captured_stdout():
    """Capture the output of sys.stdout:

       with captured_stdout() as stdout:
           print("hello")
       self.assertEqual(stdout.getvalue(), "hello\n")
    """
    return captured_output("stdout")


def captured_stderr():
    """Capture the output of sys.stderr:

       with captured_stderr() as stderr:
           print("hello", file=sys.stderr)
       self.assertEqual(stderr.getvalue(), "hello\n")
    """
    return captured_output("stderr")


def captured_stdin():
    """Capture the input to sys.stdin:

       with captured_stdin() as stdin:
           stdin.write('hello\n')
           stdin.seek(0)
           # call test code that consumes from sys.stdin
           captured = input()
       self.assertEqual(captured, "hello")
    """
    return captured_output("stdin")


def reset_warning_registry():
    """
    Clear warning registry for all modules. This is required in some tests
    because of a bug in Python that prevents warnings.simplefilter("always")
    from always making warnings appear: http://bugs.python.org/issue4180

    The bug was fixed in Python 3.4.2.
    """
    key = "__warningregistry__"
    for mod in sys.modules.values():
        if hasattr(mod, key):
            getattr(mod, key).clear()


@contextmanager
def freeze_time(t):
    """
    Context manager to temporarily freeze time.time(). This temporarily
    modifies the time function of the time module. Modules which import the
    time function directly (e.g. `from time import time`) won't be affected
    This isn't meant as a public API, but helps reduce some repetitive code in
    Django's test suite.
    """
    _real_time = time.time
    time.time = lambda: t
    try:
        yield
    finally:
        time.time = _real_time


def require_jinja2(test_func):
    """
    Decorator to enable a Jinja2 template engine in addition to the regular
    Django template engine for a test or skip it if Jinja2 isn't available.
    """
    test_func = skipIf(jinja2 is None, "this test requires jinja2")(test_func)
    test_func = override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
    }, {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'APP_DIRS': True,
        'OPTIONS': {'keep_trailing_newline': True},
    }])(test_func)
    return test_func


class ScriptPrefix(ContextDecorator):
    def __enter__(self):
        set_script_prefix(self.prefix)

    def __exit__(self, exc_type, exc_val, traceback):
        set_script_prefix(self.old_prefix)

    def __init__(self, prefix):
        self.prefix = prefix
        self.old_prefix = get_script_prefix()


def override_script_prefix(prefix):
    """
    Decorator or context manager to temporary override the script prefix.
    """
    return ScriptPrefix(prefix)


class LoggingCaptureMixin(object):
    """
    Capture the output from the 'django' logger and store it on the class's
    logger_output attribute.
    """
    def setUp(self):
        self.logger = logging.getLogger('django')
        self.old_stream = self.logger.handlers[0].stream
        self.logger_output = six.StringIO()
        self.logger.handlers[0].stream = self.logger_output

    def tearDown(self):
        self.logger.handlers[0].stream = self.old_stream
