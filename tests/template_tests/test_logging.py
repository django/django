from __future__ import unicode_literals

import logging

from django.template import Template, Variable, VariableDoesNotExist
from django.test import SimpleTestCase
from django.test.utils import override_settings


class TestHandler(logging.Handler):
    def __init__(self):
        super(TestHandler, self).__init__()
        self.log_record = None

    def emit(self, record):
        self.log_record = record


@override_settings(DEBUG=True)
class VariableResolveLoggingTests(SimpleTestCase):
    def setUp(self):
        self.test_handler = TestHandler()
        self.logger = logging.getLogger('django.template')
        self.original_level = self.logger.level
        self.logger.addHandler(self.test_handler)
        self.logger.setLevel(logging.DEBUG)

    def tearDown(self):
        self.logger.removeHandler(self.test_handler)
        self.logger.level = self.original_level

    def test_log_on_variable_does_not_exist_silent(self):
        class TestObject(object):
            class SilentDoesNotExist(Exception):
                silent_variable_failure = True

            @property
            def template_name(self):
                return "template"

            @property
            def template(self):
                return Template('')

            @property
            def article(self):
                raise TestObject.SilentDoesNotExist("Attribute does not exist.")

            def __iter__(self):
                return iter([attr for attr in dir(TestObject) if attr[:2] != "__"])

            def __getitem__(self, item):
                return self.__dict__[item]

        c = TestObject()

        Variable('article').resolve(c)
        self.assertEqual(
            self.test_handler.log_record.msg,
            'template - Attribute does not exist.'
        )

    def test_log_on_variable_does_not_exist_not_silent(self):
        c = {'article': {'section': 'News'}}

        with self.assertRaises(VariableDoesNotExist):
            Variable('article.author').resolve(c)

        self.assertEqual(
            self.test_handler.log_record.msg,
            'unknown - Failed lookup for key [author] in %r' %
            ("{%r: %r}" % ('section', 'News'), )
        )

    def test_no_log_when_variable_exists(self):
        c = {'article': {'section': 'News'}}
        Variable('article.section').resolve(c)
        self.assertIsNone(self.test_handler.log_record)
