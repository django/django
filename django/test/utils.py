import sys, time, os
from django.conf import settings
from django.db import connection
from django.core import mail
from django.core.mail.backends import locmem
from django.test import signals
from django.template import Template
from django.utils.translation import deactivate

class ContextList(list):
    """A wrapper that provides direct key access to context items contained
    in a list of context objects.
    """
    def __getitem__(self, key):
        if isinstance(key, basestring):
            for subcontext in self:
                if key in subcontext:
                    return subcontext[key]
            raise KeyError
        else:
            return super(ContextList, self).__getitem__(key)


def instrumented_test_render(self, context):
    """
    An instrumented Template render method, providing a signal
    that can be intercepted by the test system Client
    """
    signals.template_rendered.send(sender=self, template=self, context=context)
    return self.nodelist.render(context)


def setup_test_environment():
    """Perform any global pre-test setup. This involves:

        - Installing the instrumented test renderer
        - Set the email backend to the locmem email backend.
        - Setting the active locale to match the LANGUAGE_CODE setting.
    """
    Template.original_render = Template.render
    Template.render = instrumented_test_render

    mail.original_SMTPConnection = mail.SMTPConnection
    mail.SMTPConnection = locmem.EmailBackend

    mail.original_email_backend = settings.EMAIL_BACKEND
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem'

    mail.outbox = []

    deactivate()

def teardown_test_environment():
    """Perform any global post-test teardown. This involves:

        - Restoring the original test renderer
        - Restoring the email sending functions

    """
    Template.render = Template.original_render
    del Template.original_render

    mail.SMTPConnection = mail.original_SMTPConnection
    del mail.original_SMTPConnection

    settings.EMAIL_BACKEND = mail.original_email_backend
    del mail.original_email_backend

    del mail.outbox

def get_runner(settings):
    test_path = settings.TEST_RUNNER.split('.')
    # Allow for Python 2.5 relative paths
    if len(test_path) > 1:
        test_module_name = '.'.join(test_path[:-1])
    else:
        test_module_name = '.'
    test_module = __import__(test_module_name, {}, {}, test_path[-1])
    test_runner = getattr(test_module, test_path[-1])
    return test_runner
