from __future__ import with_statement

from django.core.exceptions import ValidationError
from django.core.validators import EMPTY_VALUES
from django.forms.fields import CharField
from django.test.utils import get_warnings_state, restore_warnings_state
from django.utils.unittest import TestCase


class LocalFlavorTestCase(TestCase):
    # NOTE: These are copied from the TestCase Django uses for tests which
    # access the database
    def save_warnings_state(self):
        self._warnings_state = get_warnings_state()

    def restore_warnings_state(self):
        restore_warnings_state(self._warnings_state)

    def assertFieldOutput(self, fieldclass, valid, invalid, field_args=None,
            field_kwargs=None, empty_value=u''):
        """
        Asserts that a field behaves correctly with various inputs.

        Args:
            fieldclass: the class of the field to be tested.
            valid: a dictionary mapping valid inputs to their expected
                    cleaned values.
            invalid: a dictionary mapping invalid inputs to one or more
                    raised error messages.
            field_args: the args passed to instantiate the field
            field_kwargs: the kwargs passed to instantiate the field
            empty_value: the expected clean output for inputs in EMPTY_VALUES

        """
        if field_args is None:
            field_args = []
        if field_kwargs is None:
            field_kwargs = {}
        required = fieldclass(*field_args, **field_kwargs)
        optional = fieldclass(*field_args, **dict(field_kwargs, required=False))
        # test valid inputs
        for input, output in valid.items():
            self.assertEqual(required.clean(input), output)
            self.assertEqual(optional.clean(input), output)
        # test invalid inputs
        for input, errors in invalid.items():
            with self.assertRaises(ValidationError) as context_manager:
                required.clean(input)
            self.assertEqual(context_manager.exception.messages, errors)

            with self.assertRaises(ValidationError) as context_manager:
                optional.clean(input)
            self.assertEqual(context_manager.exception.messages, errors)
        # test required inputs
        error_required = [u'This field is required.']
        for e in EMPTY_VALUES:
            with self.assertRaises(ValidationError) as context_manager:
                required.clean(e)
            self.assertEqual(context_manager.exception.messages, error_required)
            self.assertEqual(optional.clean(e), empty_value)
        # test that max_length and min_length are always accepted
        if issubclass(fieldclass, CharField):
            field_kwargs.update({'min_length':2, 'max_length':20})
            self.assertTrue(isinstance(fieldclass(*field_args, **field_kwargs), fieldclass))
