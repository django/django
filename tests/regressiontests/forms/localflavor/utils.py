from django.core.exceptions import ValidationError
from django.core.validators import EMPTY_VALUES
from django.test.utils import get_warnings_state, restore_warnings_state
from django.utils.unittest import TestCase


class LocalFlavorTestCase(TestCase):
    # NOTE: These are copied from the TestCase Django uses for tests which
    # access the database
    def save_warnings_state(self):
        self._warnings_state = get_warnings_state()

    def restore_warnings_state(self):
        restore_warnings_state(self._warnings_state)

    def assertFieldOutput(self, fieldclass, valid, invalid, field_args=[],
        field_kwargs={}, empty_value=u''):
        """Asserts that a field behaves correctly with various inputs.

        Args:
            fieldclass: the class of the field to be tested.
            valid: a dictionary mapping valid inputs to their expected
                    cleaned values.
            invalid: a dictionary mapping invalid inputs to one or more
                    raised error messages.
            fieldargs: the args passed to instantiate the field
            fieldkwargs: the kwargs passed to instantiate the field
            emptyvalue: the expected clean output for inputs in EMPTY_VALUES
        """
        required = fieldclass(*field_args, **field_kwargs)
        optional = fieldclass(*field_args, required=False, **field_kwargs)
        # test valid inputs
        for input, output in valid.items():
            self.assertEqual(required.clean(input), output)
            self.assertEqual(optional.clean(input), output)
        # test invalid inputs
        for input, errors in invalid.items():
            self.assertRaisesRegexp(ValidationError, unicode(errors),
                required.clean, input
            )
            self.assertRaisesRegexp(ValidationError, unicode(errors),
                optional.clean, input
            )
        # test required inputs
        error_required = u'This field is required'
        for e in EMPTY_VALUES:
            self.assertRaisesRegexp(ValidationError, error_required,
                required.clean, e)
            self.assertEqual(optional.clean(e), empty_value)
