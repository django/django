from __future__ import absolute_import

from django.contrib.localflavor.hk.forms import HKPhoneNumberField
from django.test import SimpleTestCase


class HKLocalFlavorTests(SimpleTestCase):
    """Tests for Hong Kong Local Flavors"""

    def test_HKPhoneNumberField(self):
        error_msgs = HKPhoneNumberField.default_error_messages
        valid = {
            '2111-1111': '2111-1111',
            '3111 1111': '3111-1111',
            '51111111': '5111-1111',
            '852-6111-1111': '6111-1111',
            '(+852) 8111-1111': '8111-1111',
            '(+852) 9111-1111': '9111-1111',
            '85291111111': '9111-1111',
        }
        invalid = {
            '9991-1111': [error_msgs['disguise'], ],
            '9921-1111': [error_msgs['disguise'], ],
            '1121-1111': [error_msgs['disguise'], ],
            '99987654': [error_msgs['disguise'], ],
            '99287654': [error_msgs['disguise'], ],
            '11287654': [error_msgs['disguise'], ],
            '1': [error_msgs['invalid'], ],
            '2111--1111': [error_msgs['invalid'], ],
            '11111111': [error_msgs['prefix'], ],
            '00000000': [error_msgs['prefix'], ],
            '44444444': [error_msgs['prefix'], ],
            '77777777': [error_msgs['prefix'], ],
        }
        self.assertFieldOutput(HKPhoneNumberField, valid, invalid)
