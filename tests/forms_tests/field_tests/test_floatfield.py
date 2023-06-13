from django.core.exceptions import ValidationError
from django.forms import FloatField, NumberInput
from django.test import SimpleTestCase
from django.test.selenium import SeleniumTestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import formats, translation

from . import FormFieldAssertionsMixin


class FloatFieldTest(FormFieldAssertionsMixin, SimpleTestCase):
    def test_floatfield_1(self):
        f = FloatField()
        self.assertWidgetRendersTo(
            f, '<input step="any" type="number" name="f" id="id_f" required>'
        )
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean("")
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(None)
        self.assertEqual(1.0, f.clean("1"))
        self.assertIsInstance(f.clean("1"), float)
        self.assertEqual(23.0, f.clean("23"))
        self.assertEqual(3.1400000000000001, f.clean("3.14"))
        self.assertEqual(3.1400000000000001, f.clean(3.14))
        self.assertEqual(42.0, f.clean(42))
        with self.assertRaisesMessage(ValidationError, "'Enter a number.'"):
            f.clean("a")
        self.assertEqual(1.0, f.clean("1.0 "))
        self.assertEqual(1.0, f.clean(" 1.0"))
        self.assertEqual(1.0, f.clean(" 1.0 "))
        with self.assertRaisesMessage(ValidationError, "'Enter a number.'"):
            f.clean("1.0a")
        self.assertIsNone(f.max_value)
        self.assertIsNone(f.min_value)
        with self.assertRaisesMessage(ValidationError, "'Enter a number.'"):
            f.clean("Infinity")
        with self.assertRaisesMessage(ValidationError, "'Enter a number.'"):
            f.clean("NaN")
        with self.assertRaisesMessage(ValidationError, "'Enter a number.'"):
            f.clean("-Inf")

    def test_floatfield_2(self):
        f = FloatField(required=False)
        self.assertIsNone(f.clean(""))
        self.assertIsNone(f.clean(None))
        self.assertEqual(1.0, f.clean("1"))
        self.assertIsNone(f.max_value)
        self.assertIsNone(f.min_value)

    def test_floatfield_3(self):
        f = FloatField(max_value=1.5, min_value=0.5)
        self.assertWidgetRendersTo(
            f,
            '<input step="any" name="f" min="0.5" max="1.5" type="number" id="id_f" '
            "required>",
        )
        with self.assertRaisesMessage(
            ValidationError, "'Ensure this value is less than or equal to 1.5.'"
        ):
            f.clean("1.6")
        with self.assertRaisesMessage(
            ValidationError, "'Ensure this value is greater than or equal to 0.5.'"
        ):
            f.clean("0.4")
        self.assertEqual(1.5, f.clean("1.5"))
        self.assertEqual(0.5, f.clean("0.5"))
        self.assertEqual(f.max_value, 1.5)
        self.assertEqual(f.min_value, 0.5)

    def test_floatfield_4(self):
        f = FloatField(step_size=0.02)
        self.assertWidgetRendersTo(
            f,
            '<input name="f" step="0.02" type="number" id="id_f" required>',
        )
        msg = "'Ensure this value is a multiple of step size 0.02.'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("0.01")
        self.assertEqual(2.34, f.clean("2.34"))
        self.assertEqual(2.1, f.clean("2.1"))
        self.assertEqual(-0.50, f.clean("-.5"))
        self.assertEqual(-1.26, f.clean("-1.26"))
        self.assertEqual(f.step_size, 0.02)

    def test_floatfield_widget_attrs(self):
        f = FloatField(widget=NumberInput(attrs={"step": 0.01, "max": 1.0, "min": 0.0}))
        self.assertWidgetRendersTo(
            f,
            '<input step="0.01" name="f" min="0.0" max="1.0" type="number" id="id_f" '
            "required>",
        )

    def test_floatfield_localized(self):
        """
        A localized FloatField's widget renders to a text input without any
        number input specific attributes.
        """
        f = FloatField(localize=True)
        self.assertWidgetRendersTo(f, '<input id="id_f" name="f" type="text" required>')

    def test_floatfield_changed(self):
        f = FloatField()
        n = 4.35
        self.assertFalse(f.has_changed(n, "4.3500"))

        with translation.override("fr"):
            f = FloatField(localize=True)
            localized_n = formats.localize_input(n)  # -> '4,35' in French
            self.assertFalse(f.has_changed(n, localized_n))

    @override_settings(DECIMAL_SEPARATOR=",")
    def test_floatfield_support_decimal_separator(self):
        with translation.override(None):
            f = FloatField(localize=True)
            self.assertEqual(f.clean("1001,10"), 1001.10)
            self.assertEqual(f.clean("1001.10"), 1001.10)

    @override_settings(
        DECIMAL_SEPARATOR=",",
        USE_THOUSAND_SEPARATOR=True,
        THOUSAND_SEPARATOR=".",
    )
    def test_floatfield_support_thousands_separator(self):
        with translation.override(None):
            f = FloatField(localize=True)
            self.assertEqual(f.clean("1.001,10"), 1001.10)
            msg = "'Enter a number.'"
            with self.assertRaisesMessage(ValidationError, msg):
                f.clean("1,001.1")


@override_settings(ROOT_URLCONF="forms_tests.urls")
class FloatFieldHTMLTest(SeleniumTestCase):
    available_apps = ["forms_tests"]

    def test_float_field_rendering_passes_client_side_validation(self):
        """
        Rendered widget allows non-integer value with the client-side
        validation.
        """
        from selenium.webdriver.common.by import By

        self.selenium.get(self.live_server_url + reverse("form_view"))
        number_input = self.selenium.find_element(By.ID, "id_number")
        number_input.send_keys("0.5")
        is_valid = self.selenium.execute_script(
            "return document.getElementById('id_number').checkValidity()"
        )
        self.assertTrue(is_valid)
