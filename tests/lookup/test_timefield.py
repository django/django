from __future__ import unicode_literals

from django.test import TestCase

from .models import Alarm


class TimeFieldLookupTests(TestCase):

    @classmethod
    def setUpTestData(self):
        # Create a few Alarms
        self.al1 = Alarm.objects.create(desc='Early', time='05:30')
        self.al2 = Alarm.objects.create(desc='Late', time='10:00')
        self.al3 = Alarm.objects.create(desc='Precise', time='12:34:56')

    def test_hour_lookups(self):
        self.assertQuerysetEqual(
            Alarm.objects.filter(time__hour=5),
            ['<Alarm: 05:30:00 (Early)>'],
            ordered=False
        )

    def test_minute_lookups(self):
        self.assertQuerysetEqual(
            Alarm.objects.filter(time__minute=30),
            ['<Alarm: 05:30:00 (Early)>'],
            ordered=False
        )

    def test_second_lookups(self):
        self.assertQuerysetEqual(
            Alarm.objects.filter(time__second=56),
            ['<Alarm: 12:34:56 (Precise)>'],
            ordered=False
        )
