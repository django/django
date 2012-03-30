import warnings
from django.conf import settings, UserSettingsHolder
from django.core import mail
from django.test.signals import template_rendered, setting_changed
from django.template import Template, loader, TemplateDoesNotExist
from django.template.loaders import cached
from django.utils.translation import deactivate
from django.utils.functional import wraps


__all__ = (
    'Approximate', 'ContextList',  'get_runner', 'override_settings',
    'setup_test_environment', 'teardown_test_environment',
)

RESTORE_LOADERS_ATTR = '_original_template_source_loaders'


class Approximate(object):
    def __init__(self, val, places=7):
        self.val = val
        self.places = places

    def __repr__(self):
        return repr(self.val)

    def __eq__(self, other):
        if self.val == other:
            return True
        return round(abs(self.val-other), self.places) == 0


class ContextList(list):
    """A wrapper that provides direct key access to context items contained
    in a list of context objects.
    """
    def __getitem__(self, key):
        if isinstance(key, basestring):
            for subcontext in self:
                if key in subcontext:
                    return subcontext[key]
            raise KeyError(key)
        else:
            return super(ContextList, self).__getitem__(key)

    def __contains__(self, key):
        try:
            value = self[key]
        except KeyError:
            return False
        return True


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
    Template.original_render = Template._render
    Template._render = instrumented_test_render

    mail.original_email_backend = settings.EMAIL_BACKEND
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

    mail.outbox = []

    deactivate()


def teardown_test_environment():
    """Perform any global post-test teardown. This involves:

        - Restoring the original test renderer
        - Restoring the email sending functions

    """
    Template._render = Template.original_render
    del Template.original_render

    settings.EMAIL_BACKEND = mail.original_email_backend
    del mail.original_email_backend

    del mail.outbox


def get_warnings_state():
    """
    Returns an object containing the state of the warnings module
    """
    # There is no public interface for doing this, but this implementation of
    # get_warnings_state and restore_warnings_state appears to work on Python
    # 2.4 to 2.7.
    return warnings.filters[:]


def restore_warnings_state(state):
    """
    Restores the state of the warnings module when passed an object that was
    returned by get_warnings_state()
    """
    warnings.filters = state[:]


def get_runner(settings, test_runner_class=None):
    if not test_runner_class:
        test_runner_class = settings.TEST_RUNNER

    test_path = test_runner_class.split('.')
    # Allow for Python 2.5 relative paths
    if len(test_path) > 1:
        test_module_name = '.'.join(test_path[:-1])
    else:
        test_module_name = '.'
    test_module = __import__(test_module_name, {}, {}, test_path[-1])
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
        self.wrapped = settings._wrapped

    def __enter__(self):
        self.enable()

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable()

    def __call__(self, test_func):
        from django.test import TransactionTestCase
        if isinstance(test_func, type) and issubclass(test_func, TransactionTestCase):
            original_pre_setup = test_func._pre_setup
            original_post_teardown = test_func._post_teardown
            def _pre_setup(innerself):
                self.enable()
                original_pre_setup(innerself)
            def _post_teardown(innerself):
                original_post_teardown(innerself)
                self.disable()
            test_func._pre_setup = _pre_setup
            test_func._post_teardown = _post_teardown
            return test_func
        else:
            @wraps(test_func)
            def inner(*args, **kwargs):
                with self:
                    return test_func(*args, **kwargs)
        return inner

    def enable(self):
        override = UserSettingsHolder(settings._wrapped)
        for key, new_value in self.options.items():
            setattr(override, key, new_value)
        settings._wrapped = override
        for key, new_value in self.options.items():
            setting_changed.send(sender=settings._wrapped.__class__,
                                 setting=key, value=new_value)

    def disable(self):
        settings._wrapped = self.wrapped
        for key in self.options:
            new_value = getattr(settings, key, None)
            setting_changed.send(sender=settings._wrapped.__class__,
                                 setting=key, value=new_value)

