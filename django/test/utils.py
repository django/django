from contextlib import contextmanager
import logging
import re
import sys
import time
from unittest import skipUnless
import warnings
from functools import wraps
from xml.dom.minidom import parseString, Node

from django.apps import apps
from django.conf import settings, UserSettingsHolder
from django.core import mail
from django.core.signals import request_started
from django.db import reset_queries
from django.http import request
from django.template import Template, loader, TemplateDoesNotExist
from django.template.loaders import cached
from django.test.signals import template_rendered, setting_changed
from django.utils import six
from django.utils.deprecation import RemovedInDjango18Warning, RemovedInDjango19Warning
from django.utils.encoding import force_str
from django.utils.translation import deactivate


__all__ = (
    'Approximate', 'ContextList', 'get_runner',
    'modify_settings', 'override_settings',
    'requires_tz_support',
    'setup_test_environment', 'teardown_test_environment',
)

RESTORE_LOADERS_ATTR = '_original_template_source_loaders'
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


def setup_test_template_loader(templates_dict, use_cached_loader=False):
    """
    Changes Django to only find templates from within a dictionary (where each
    key is the template name and each value is the corresponding template
    content to return).

    Use meth:`restore_template_loaders` to restore the original loaders.
    """
    if hasattr(loader, RESTORE_LOADERS_ATTR):
        raise Exception("loader.%s already exists" % RESTORE_LOADERS_ATTR)

    def test_template_loader(template_name, template_dirs=None):
        "A custom template loader that loads templates from a dictionary."
        try:
            return (templates_dict[template_name], "test:%s" % template_name)
        except KeyError:
            raise TemplateDoesNotExist(template_name)

    if use_cached_loader:
        template_loader = cached.Loader(('test_template_loader',))
        template_loader._cached_loaders = (test_template_loader,)
    else:
        template_loader = test_template_loader

    setattr(loader, RESTORE_LOADERS_ATTR, loader.template_source_loaders)
    loader.template_source_loaders = (template_loader,)
    return template_loader


def restore_template_loaders():
    """
    Restores the original template loaders after
    :meth:`setup_test_template_loader` has been run.
    """
    loader.template_source_loaders = getattr(loader, RESTORE_LOADERS_ATTR)
    delattr(loader, RESTORE_LOADERS_ATTR)


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
            # Hack used when instantiating from SimpleTestCase._pre_setup.
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
                # When called from SimpleTestCase._pre_setup, values may be
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


def override_system_checks(new_checks):
    """ Acts as a decorator. Overrides list of registered system checks.
    Useful when you override `INSTALLED_APPS`, e.g. if you exclude `auth` app,
    you also need to exclude its system checks. """

    from django.core.checks.registry import registry

    def outer(test_func):
        @wraps(test_func)
        def inner(*args, **kwargs):
            old_checks = registry.registered_checks
            registry.registered_checks = new_checks
            try:
                return test_func(*args, **kwargs)
            finally:
                registry.registered_checks = old_checks
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
        return ''.join([c.data for c in element.childNodes
                        if c.nodeType == Node.TEXT_NODE])

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
        self.use_debug_cursor = self.connection.use_debug_cursor
        self.connection.use_debug_cursor = True
        self.initial_queries = len(self.connection.queries)
        self.final_queries = None
        request_started.disconnect(reset_queries)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.use_debug_cursor = self.use_debug_cursor
        request_started.connect(reset_queries)
        if exc_type is not None:
            return
        self.final_queries = len(self.connection.queries)


class IgnoreDeprecationWarningsMixin(object):
    warning_classes = [RemovedInDjango18Warning]

    def setUp(self):
        super(IgnoreDeprecationWarningsMixin, self).setUp()
        self.catch_warnings = warnings.catch_warnings()
        self.catch_warnings.__enter__()
        for warning_class in self.warning_classes:
            warnings.filterwarnings("ignore", category=warning_class)

    def tearDown(self):
        self.catch_warnings.__exit__(*sys.exc_info())
        super(IgnoreDeprecationWarningsMixin, self).tearDown()


class IgnorePendingDeprecationWarningsMixin(IgnoreDeprecationWarningsMixin):
        warning_classes = [RemovedInDjango19Warning]


class IgnoreAllDeprecationWarningsMixin(IgnoreDeprecationWarningsMixin):
        warning_classes = [RemovedInDjango19Warning, RemovedInDjango18Warning]


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
