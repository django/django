import sys, time, os
from django.conf import settings
from django.db import connection
from django.core import mail
from django.test import signals
from django.template import Template
from django.utils.translation import deactivate

def instrumented_test_render(self, context):
    """
    An instrumented Template render method, providing a signal
    that can be intercepted by the test system Client
    """
    signals.template_rendered.send(sender=self, template=self, context=context)
    return self.nodelist.render(context)

class TestSMTPConnection(object):
    """A substitute SMTP connection for use during test sessions.
    The test connection stores email messages in a dummy outbox,
    rather than sending them out on the wire.

    """
    def __init__(*args, **kwargs):
        pass
    def open(self):
        "Mock the SMTPConnection open() interface"
        pass
    def close(self):
        "Mock the SMTPConnection close() interface"
        pass
    def send_messages(self, messages):
        "Redirect messages to the dummy outbox"
        mail.outbox.extend(messages)
        return len(messages)

def setup_test_environment():
    """Perform any global pre-test setup. This involves:

        - Installing the instrumented test renderer
        - Diverting the email sending functions to a test buffer
        - Setting the active locale to match the LANGUAGE_CODE setting.
    """
    Template.original_render = Template.render
    Template.render = instrumented_test_render

    mail.original_SMTPConnection = mail.SMTPConnection
    mail.SMTPConnection = TestSMTPConnection

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

    del mail.outbox

