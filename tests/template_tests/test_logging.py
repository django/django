import logging

from django.template import Engine, Variable, VariableDoesNotExist
from django.test import SimpleTestCase


class TestHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_record = None

    def emit(self, record):
        self.log_record = record


class BaseTemplateLoggingTestCase(SimpleTestCase):
    def setUp(self):
        self.test_handler = TestHandler()
        self.logger = logging.getLogger('django.template')
        self.original_level = self.logger.level
        self.logger.addHandler(self.test_handler)
        self.logger.setLevel(self.loglevel)

    def tearDown(self):
        self.logger.removeHandler(self.test_handler)
        self.logger.level = self.original_level


class VariableResolveLoggingTests(BaseTemplateLoggingTestCase):
    loglevel = logging.DEBUG

    def test_log_on_variable_does_not_exist_silent(self):
        class TestObject:
            class SilentDoesNotExist(Exception):
                silent_variable_failure = True

            @property
            def template_name(self):
                return "template_name"

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
            self.test_handler.log_record.getMessage(),
            "Exception while resolving variable 'article' in template 'template_name'."
        )
        self.assertIsNotNone(self.test_handler.log_record.exc_info)
        raised_exception = self.test_handler.log_record.exc_info[1]
        self.assertEqual(str(raised_exception), 'Attribute does not exist.')

    def test_log_on_variable_does_not_exist_not_silent(self):
        with self.assertRaises(VariableDoesNotExist):
            Variable('article.author').resolve({'article': {'section': 'News'}})

        self.assertEqual(
            self.test_handler.log_record.getMessage(),
            "Exception while resolving variable 'author' in template 'unknown'."
        )
        self.assertIsNotNone(self.test_handler.log_record.exc_info)
        raised_exception = self.test_handler.log_record.exc_info[1]
        self.assertEqual(
            str(raised_exception),
            "Failed lookup for key [author] in {'section': 'News'}"
        )

    def test_no_log_when_variable_exists(self):
        Variable('article.section').resolve({'article': {'section': 'News'}})
        self.assertIsNone(self.test_handler.log_record)
