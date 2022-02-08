import datetime

from django.core.exceptions import ValidationError
from django.forms import DurationField
from django.test import SimpleTestCase
from django.utils import translation
from django.utils.duration import duration_string

from . import FormFieldAssertionsMixin


class DurationFieldTest(FormFieldAssertionsMixin, SimpleTestCase):
    def test_durationfield_clean(self):
        f = DurationField()
        self.assertEqual(datetime.timedelta(seconds=30), f.clean("30"))
        self.assertEqual(datetime.timedelta(minutes=15, seconds=30), f.clean("15:30"))
        self.assertEqual(
            datetime.timedelta(hours=1, minutes=15, seconds=30), f.clean("1:15:30")
        )
        self.assertEqual(
            datetime.timedelta(
                days=1, hours=1, minutes=15, seconds=30, milliseconds=300
            ),
            f.clean("1 1:15:30.3"),
        )
        self.assertEqual(
            datetime.timedelta(0, 10800),
            f.clean(datetime.timedelta(0, 10800)),
        )
        msg = "This field is required."
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("")
        msg = "Enter a valid duration."
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("not_a_time")

    def test_durationfield_clean_not_required(self):
        f = DurationField(required=False)
        self.assertIsNone(f.clean(""))

    def test_overflow(self):
        msg = "The number of days must be between {min_days} and {max_days}.".format(
            min_days=datetime.timedelta.min.days,
            max_days=datetime.timedelta.max.days,
        )
        f = DurationField()
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("1000000000 00:00:00")
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("-1000000000 00:00:00")

    def test_overflow_translation(self):
        msg = "Le nombre de jours doit être entre {min_days} et {max_days}.".format(
            min_days=datetime.timedelta.min.days,
            max_days=datetime.timedelta.max.days,
        )
        with translation.override("fr"):
            with self.assertRaisesMessage(ValidationError, msg):
                DurationField().clean("1000000000 00:00:00")

    def test_durationfield_render(self):
        self.assertWidgetRendersTo(
            DurationField(initial=datetime.timedelta(hours=1)),
            '<input id="id_f" type="text" name="f" value="01:00:00" required>',
        )

    def test_durationfield_integer_value(self):
        f = DurationField()
        self.assertEqual(datetime.timedelta(0, 10800), f.clean(10800))

    def test_durationfield_prepare_value(self):
        field = DurationField()
        td = datetime.timedelta(minutes=15, seconds=30)
        self.assertEqual(field.prepare_value(td), duration_string(td))
        self.assertEqual(field.prepare_value("arbitrary"), "arbitrary")
        self.assertIsNone(field.prepare_value(None))
