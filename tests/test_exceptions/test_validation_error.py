import unittest

from django.core.exceptions import ValidationError
from django.utils import six
from django.utils.safestring import SafeData, mark_safe


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

    def test_iter_ouput_respects_safe_data(self):
        ve = ValidationError(mark_safe('safe'))
        self.assertIsInstance(list(ve)[0], SafeData)
        ve = ValidationError(mark_safe('%(r)s'), params={'r': 'replaced'})
        self.assertIsInstance(list(ve)[0], six.text_type)
        ve = ValidationError(mark_safe('%(r)s'),
                             params={'r': mark_safe('safe replaced')})
        self.assertIsInstance(list(ve)[0], SafeData)
        ve = ValidationError(mark_safe('%(r)s %(s)s'),
                             params={'r': mark_safe('actually'),
                                     's': 'not safe'})
        self.assertIsInstance(list(ve)[0], six.text_type)
        ve = ValidationError(mark_safe('%(r)s %(s)s'),
                             params={'r': mark_safe('this is'),
                                     's': mark_safe('safe')})
        self.assertIsInstance(list(ve)[0], SafeData)
