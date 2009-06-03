from unittest import TestCase

from django.core.exceptions import ValidationError
from django.core.validators import validate_integer, validate_email

class TestSimpleValidators(TestCase):
    pass

SIMPLE_VALIDATORS_VALUES = (
    (validate_integer, '42', None),
    (validate_integer, '-42', None),
    (validate_integer, -42, None),
    (validate_integer, -42.5, None),
    (validate_integer, None, ValidationError),
    (validate_integer, 'a', ValidationError),
    (validate_email, 'email@here.com', None),
    (validate_email, 'weirder-email@here.and.there.com', None),
    (validate_email, None, ValidationError),
    (validate_email, '', ValidationError),
    (validate_email, 'abc', ValidationError),
    (validate_email, 'a @x.cz', ValidationError),
    (validate_email, 'something@@somewhere.com', ValidationError),
)

def get_simple_test_func(validator, expected, value, num):
    if isinstance(expected, type) and issubclass(expected, ValidationError):
        test_mask = 'test_%s_raises_error_%d'
        def test_func(self):
            self.assertRaises(expected, validator, value)
    else:
        test_mask = 'test_%s_%d'
        def test_func(self):
            self.assertEqual(expected, validator(value))
    test_name = test_mask % (validator.__name__, num)
    return test_name, test_func

test_counter = {}
for validator, value, expected in SIMPLE_VALIDATORS_VALUES:
    num = test_counter[validator] = test_counter.setdefault(validator, 0) + 1
    setattr(TestSimpleValidators, *get_simple_test_func(validator, expected, value, num))
