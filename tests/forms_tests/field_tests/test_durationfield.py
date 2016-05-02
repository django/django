from __future__ import unicode_literals

import datetime

from django.forms import DurationField
from django.test import SimpleTestCase
from django.utils.duration import duration_string

from . import FormFieldAssertionsMixin


class DurationFieldTest(FormFieldAssertionsMixin, SimpleTestCase):

    def test_durationfield_clean(self):
        f = DurationField()
        self.assertEqual(datetime.timedelta(seconds=30), f.clean('30'))
        self.assertEqual(datetime.timedelta(minutes=15, seconds=30), f.clean('15:30'))
        self.assertEqual(datetime.timedelta(hours=1, minutes=15, seconds=30), f.clean('1:15:30'))
        self.assertEqual(
            datetime.timedelta(days=1, hours=1, minutes=15, seconds=30, milliseconds=300),
            f.clean('1 1:15:30.3')
        )

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
        self.assertEqual(field.prepare_value('arbitrary'), 'arbitrary')
        self.assertIsNone(field.prepare_value(None))
