from django.core.exceptions import ValidationError
from django.core.validators import EMPTY_VALUES
from django.utils.unittest import TestCase


class LocalFlavorTestCase(TestCase):
    def assertFieldOutput(self, fieldclass, valid, invalid):
        """Asserts that a field behaves correctly with various inputs.

        Args:
            fieldclass: the class of the field to be tested.
            valid: a dictionary mapping valid inputs to their expected
                    cleaned values.
            invalid: a dictionary mapping invalid inputs to one or more
                    raised error messages.
        """

        required = fieldclass()
        optional = fieldclass(required=False)
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
                required.clean, e
            )
            self.assertEqual(optional.clean(e), u'')
