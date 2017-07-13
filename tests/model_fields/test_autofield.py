from django.test import TestCase

from .models import AutoModel, BigAutoModel, SmallAutoModel


class AutoFieldTests(TestCase):
    model = AutoModel

    def test_invalid_value(self):
        tests = [
            (TypeError, ()),
            (TypeError, []),
            (TypeError, {}),
            (TypeError, set()),
            (TypeError, object()),
            (TypeError, complex()),
            (ValueError, 'non-numeric string'),
            (ValueError, b'non-numeric byte-string'),
        ]
        for exception, value in tests:
            with self.subTest(value=value):
                msg = "Field 'value' expected a number but got %r." % (value,)
                with self.assertRaisesMessage(exception, msg):
                    self.model.objects.create(value=value)


class BigAutoFieldTests(AutoFieldTests):
    model = BigAutoModel


class SmallAutoFieldTests(AutoFieldTests):
    model = SmallAutoModel
