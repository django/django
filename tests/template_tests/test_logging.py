from __future__ import unicode_literals

import logging

from django.template import Engine, Variable, VariableDoesNotExist
from django.test import SimpleTestCase


class TestHandler(logging.Handler):
    def __init__(self):
        super(TestHandler, self).__init__()
        self.log_record = None

    def emit(self, record):
        self.log_record = record


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
                return Engine().from_string('')

            @property
            def article(self):
                raise TestObject.SilentDoesNotExist("Attribute does not exist.")

            def __iter__(self):
                return iter(attr for attr in dir(TestObject) if attr[:2] != "__")

            def __getitem__(self, item):
                return self.__dict__[item]

        Variable('article').resolve(TestObject())
        self.assertEqual(
            self.test_handler.log_record.msg,
            'template - Attribute does not exist.'
        )

    def test_log_on_variable_does_not_exist_not_silent(self):
        with self.assertRaises(VariableDoesNotExist):
            Variable('article.author').resolve({'article': {'section': 'News'}})

        self.assertEqual(
            self.test_handler.log_record.msg,
            'unknown - Failed lookup for key [author] in %r' %
            ("{%r: %r}" % ('section', 'News'), )
        )

    def test_no_log_when_variable_exists(self):
        Variable('article.section').resolve({'article': {'section': 'News'}})
        self.assertIsNone(self.test_handler.log_record)
