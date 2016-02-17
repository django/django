import unittest

from django.core.exceptions import ValidationError
from django.test import ignore_warnings
from django.utils.deprecation import RemovedInDjango20Warning


class TestValidationError(unittest.TestCase):
    def test_messages_concatenates_error_dict_values(self):
        message_dict = {}
        exception = ValidationError(message_dict)
        self.assertEqual(sorted(exception.messages), [])
        message_dict['field1'] = ['E1', 'E2']
        exception = ValidationError(message_dict)
        self.assertEqual(sorted(exception.messages), ['E1', 'E2'])
        message_dict['field2'] = ['E3', 'E4']
        exception = ValidationError(message_dict)
        self.assertEqual(sorted(exception.messages), ['E1', 'E2', 'E3', 'E4'])

    @ignore_warnings(category=RemovedInDjango20Warning)
    def test_percent_placeholders(self):
        e = ValidationError(
            'Invalid value: %s',
            params=('42',),
        )
        self.assertEqual(list(e), ['Invalid value: 42'])
        e = ValidationError(
            'Invalid value: %s, %s',
            params=('foo', 'bar'),
        )
        self.assertEqual(list(e), ['Invalid value: foo, bar'])
        e = ValidationError(
            'Invalid value: %(value)s',
            params={'value': '42'},
        )
        self.assertEqual(list(e), ['Invalid value: 42'])
        e = ValidationError(
            'Invalid value: %(value)d',
            params={'value': 42},
        )
        self.assertEqual(list(e), ['Invalid value: 42'])
        e = ValidationError(
            'Invalid value: %(value1)s, %(value2)s',
            params={'value1': 'foo', 'value2': 'bar'},
        )
        self.assertEqual(list(e), ['Invalid value: foo, bar'])

    def test_str_format_placeholders(self):
        e = ValidationError(
            'Invalid value: {value}',
            params={'value': '42'},
        )
        self.assertEqual(list(e), ['Invalid value: 42'])
        e = ValidationError(
            'Invalid value: {value:d}',
            params={'value': 42},
        )
        self.assertEqual(list(e), ['Invalid value: 42'])
        e = ValidationError(
            'Invalid value: {value1}, {value2}',
            params={'value1': 'foo', 'value2': 'bar'},
        )
        self.assertEqual(list(e), ['Invalid value: foo, bar'])
