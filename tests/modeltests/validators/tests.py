# -*- coding: utf-8 -*-
import types
from unittest import TestCase
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.core.validators import (
        validate_integer, validate_email, validate_slug, validate_ipv4_address,
        validate_comma_separated_integer_list, MaxValueValidator,
        MinValueValidator, MaxLengthValidator, MinLengthValidator,
        RequiredIfOtherFieldBlank,
    )

now = datetime.now()
class TestSimpleValidators(TestCase):
    pass

SIMPLE_VALIDATORS_VALUES = (
    # (validator, value, expected),
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


    (validate_slug, 'slug-ok', None),
    (validate_slug, 'longer-slug-still-ok', None),
    (validate_slug, '--------', None),
    (validate_slug, 'nohyphensoranything', None),

    (validate_slug, '', ValidationError),
    (validate_slug, ' text ', ValidationError),
    (validate_slug, ' ', ValidationError),
    (validate_slug, 'some@mail.com', ValidationError),
    (validate_slug, '你好', ValidationError),
    (validate_slug, '\n', ValidationError),


    (validate_ipv4_address, '1.1.1.1', None),
    (validate_ipv4_address, '255.0.0.0', None),
    (validate_ipv4_address, '0.0.0.0', None),

    (validate_ipv4_address, '256.1.1.1', ValidationError),
    (validate_ipv4_address, '25.1.1.', ValidationError),
    (validate_ipv4_address, '25,1,1,1', ValidationError),
    (validate_ipv4_address, '25.1 .1.1', ValidationError),

    (validate_comma_separated_integer_list, '1', None),
    (validate_comma_separated_integer_list, '1,2,3', None),
    (validate_comma_separated_integer_list, '1,2,3,', None),

    (validate_comma_separated_integer_list, '', ValidationError),
    (validate_comma_separated_integer_list, 'a,b,c', ValidationError),
    (validate_comma_separated_integer_list, '1, 2, 3', ValidationError),

    (MaxValueValidator(10), 10, None),
    (MaxValueValidator(10), -10, None),
    (MaxValueValidator(10), 0, None),
    (MaxValueValidator(now), now, None),
    (MaxValueValidator(now), now - timedelta(days=1), None),

    (MaxValueValidator(0), 1, ValidationError),
    (MaxValueValidator(now), now + timedelta(days=1), ValidationError),

    (MinValueValidator(-10), -10, None),
    (MinValueValidator(-10), 10, None),
    (MinValueValidator(-10), 0, None),
    (MinValueValidator(now), now, None),
    (MinValueValidator(now), now + timedelta(days=1), None),

    (MinValueValidator(0), -1, ValidationError),
    (MinValueValidator(now), now - timedelta(days=1), ValidationError),

    (MaxLengthValidator(10), '', None),
    (MaxLengthValidator(10), 10*'x', None),

    (MaxLengthValidator(10), 15*'x', ValidationError),

    (MinLengthValidator(10), 15*'x', None),
    (MinLengthValidator(10), 10*'x', None),

    (MinLengthValidator(10), '', ValidationError),

)

def get_simple_test_func(validator, expected, value, num):
    if isinstance(expected, type) and issubclass(expected, Exception):
        test_mask = 'test_%s_raises_error_%d'
        def test_func(self):
            self.assertRaises(expected, validator, value)
    else:
        test_mask = 'test_%s_%d'
        def test_func(self):
            self.assertEqual(expected, validator(value))
    if isinstance(validator, types.FunctionType):
        val_name = validator.__name__
    else:
        val_name = validator.__class__.__name__
    test_name = test_mask % (val_name, num)
    return test_name, test_func

test_counter = 0
for validator, value, expected in SIMPLE_VALIDATORS_VALUES:
    setattr(TestSimpleValidators, *get_simple_test_func(validator, expected, value, test_counter))
    test_counter += 1

class TestComplexValidators(TestCase):
    pass

COMPLEX_VALIDATORS_VALUES = (
    #(validator, value, all_values, obj, expected),
    (RequiredIfOtherFieldBlank('other'), 'given', {'other': 'given'}, None, None),
    (RequiredIfOtherFieldBlank('other'), '', {'other': 'given'}, None, None),
    (RequiredIfOtherFieldBlank('other'), 'given', {}, None, AssertionError),
    (RequiredIfOtherFieldBlank('other'), '', {}, None, AssertionError),
    (RequiredIfOtherFieldBlank('other'), '', {'other': ''}, None, ValidationError),
)

def get_complex_test_func(validator, expected, value, all_values, obj, num):
    if isinstance(expected, type) and issubclass(expected, Exception):
        test_mask = 'test_%s_raises_error_%d'
        def test_func(self):
            self.assertRaises(expected, validator, value, all_values=all_values, obj=obj)
    else:
        test_mask = 'test_%s_%d'
        def test_func(self):
            self.assertEqual(expected, validator(value, all_values=all_values, obj=obj))
    test_name = test_mask % (validator.__class__.__name__, num)
    return test_name, test_func

test_counter = {}
for validator, value, all_values, obj, expected in COMPLEX_VALIDATORS_VALUES:
    num = test_counter[validator.__class__.__name__] = test_counter.setdefault(validator.__class__.__name__, 0) + 1
    setattr(TestComplexValidators, *get_complex_test_func(validator, expected, value, all_values, obj, num))

