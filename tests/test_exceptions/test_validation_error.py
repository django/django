import unittest

from django.core.exceptions import ValidationError


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

    def test_simple_string_error_equality(self):
        exception_a = ValidationError('message')
        exception_b = ValidationError('message')
        self.assertEqual(exception_a, exception_b)

        exception_a = ValidationError(
            'e1 %(parm1)s %(parm2)s', code='my_code', params={'parm1': 'val1', 'parm2': 'val2'}
        )
        exception_b = ValidationError(
            'e1 %(parm1)s %(parm2)s', code='my_code', params={'parm2': 'val2', 'parm1': 'val1'}
        )
        self.assertEqual(exception_a, exception_b)

        exception_b = ValidationError('e1 %(parm1)s %(parm2)s', params={'parm2': 'val2', 'parm1': 'val1'})
        self.assertNotEqual(exception_a, exception_b)

        exception_b = ValidationError('e1 %(parm1)s %(parm2)s', params={'parm2': 'val2'})
        self.assertNotEqual(exception_a, exception_b)

    def test_error_dict_message_equality(self):
        exception_a = ValidationError({'field1': 'field error', 'field2': 'err'})
        exception_b = ValidationError({'field2': 'err', 'field1': 'field error'})
        self.assertEqual(exception_a, exception_b)

        exception_b = ValidationError({'field1': 'field error', 'field2': 'error 2'})
        self.assertNotEqual(exception_a, exception_b)

        exception_b = ValidationError({'field1': 'field error'})
        self.assertNotEqual(exception_a, exception_b)

        error_dict = {
            'field1': ValidationError('nice error %(parm1)s', code='my_code', params={'parm1': 'val1'}),
            'field2': 'err'
        }
        exception_a = ValidationError(error_dict)
        exception_b = ValidationError(dict(error_dict))
        self.assertEqual(exception_a, exception_b)

    def test_error_list_message_equality(self):
        error_list = [ValidationError({'field1': 'field error', 'field2': 'err'}), 'simple error']
        exception_a = ValidationError(error_list)
        exception_b = ValidationError(list(error_list))
        self.assertEqual(exception_a, exception_b)

        exception_a = ValidationError([ValidationError({'field1': 'field error', 'field2': 'err'}), 'simple error'])
        exception_b = ValidationError([ValidationError({'field1': 'field error', 'field2': 'err'}), 'diff error'])
        self.assertNotEqual(exception_a, exception_b)

    def test_equality_on_different_message_types(self):
        # message type is referring to `message` being either a simple str, an `error_list` or `error_dict`
        exception_str = ValidationError('e1 %(parm1)s', code='my_code', params={'parm1': 'val1'})
        exception_list = ValidationError([ValidationError('e1 %(parm1)s', code='my_code', params={'parm1': 'val1'})])
        exception_dict = ValidationError(
            {'field1': ValidationError('e1 %(parm1)s', code='my_code', params={'parm1': 'val1'})}
        )
        self.assertNotEqual(exception_str, exception_list)
        self.assertNotEqual(exception_list, exception_dict)
