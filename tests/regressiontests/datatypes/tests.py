from __future__ import absolute_import

import datetime

from django.test import TestCase, skipIfDBFeature
from django.utils.timezone import utc

from .models import Donut, RumBaba


class DataTypesTestCase(TestCase):

    def test_boolean_type(self):
        d = Donut(name='Apple Fritter')
        self.assertFalse(d.is_frosted)
        self.assertTrue(d.has_sprinkles is None)
        d.has_sprinkles = True
        self.assertTrue(d.has_sprinkles)

        d.save()

        d2 = Donut.objects.get(name='Apple Fritter')
        self.assertFalse(d2.is_frosted)
        self.assertTrue(d2.has_sprinkles)

    def test_date_type(self):
        d = Donut(name='Apple Fritter')
        d.baked_date = datetime.date(year=1938, month=6, day=4)
        d.baked_time = datetime.time(hour=5, minute=30)
        d.consumed_at = datetime.datetime(year=2007, month=4, day=20, hour=16, minute=19, second=59)
        d.save()

        d2 = Donut.objects.get(name='Apple Fritter')
        self.assertEqual(d2.baked_date, datetime.date(1938, 6, 4))
        self.assertEqual(d2.baked_time, datetime.time(5, 30))
        self.assertEqual(d2.consumed_at, datetime.datetime(2007, 4, 20, 16, 19, 59))

    def test_time_field(self):
        #Test for ticket #12059: TimeField wrongly handling datetime.datetime object.
        d = Donut(name='Apple Fritter')
        d.baked_time = datetime.datetime(year=2007, month=4, day=20, hour=16, minute=19, second=59)
        d.save()

        d2 = Donut.objects.get(name='Apple Fritter')
        self.assertEqual(d2.baked_time, datetime.time(16, 19, 59))

    def test_year_boundaries(self):
        """Year boundary tests (ticket #3689)"""
        d = Donut.objects.create(name='Date Test 2007',
             baked_date=datetime.datetime(year=2007, month=12, day=31),
             consumed_at=datetime.datetime(year=2007, month=12, day=31, hour=23, minute=59, second=59))
        d1 = Donut.objects.create(name='Date Test 2006',
            baked_date=datetime.datetime(year=2006, month=1, day=1),
            consumed_at=datetime.datetime(year=2006, month=1, day=1))

        self.assertEqual("Date Test 2007",
                         Donut.objects.filter(baked_date__year=2007)[0].name)

        self.assertEqual("Date Test 2006",
                         Donut.objects.filter(baked_date__year=2006)[0].name)

        d2 = Donut.objects.create(name='Apple Fritter',
            consumed_at = datetime.datetime(year=2007, month=4, day=20, hour=16, minute=19, second=59))

        self.assertEqual([u'Apple Fritter', u'Date Test 2007'],
            list(Donut.objects.filter(consumed_at__year=2007).order_by('name').values_list('name', flat=True)))

        self.assertEqual(0, Donut.objects.filter(consumed_at__year=2005).count())
        self.assertEqual(0, Donut.objects.filter(consumed_at__year=2008).count())

    def test_textfields_unicode(self):
        """Regression test for #10238: TextField values returned from the
        database should be unicode."""
        d = Donut.objects.create(name=u'Jelly Donut', review=u'Outstanding')
        newd = Donut.objects.get(id=d.id)
        self.assertTrue(isinstance(newd.review, unicode))

    @skipIfDBFeature('supports_timezones')
    def test_error_on_timezone(self):
        """Regression test for #8354: the MySQL and Oracle backends should raise
        an error if given a timezone-aware datetime object."""
        dt = datetime.datetime(2008, 8, 31, 16, 20, tzinfo=utc)
        d = Donut(name='Bear claw', consumed_at=dt)
        self.assertRaises(ValueError, d.save)
        # ValueError: MySQL backend does not support timezone-aware datetimes.

    def test_datefield_auto_now_add(self):
        """Regression test for #10970, auto_now_add for DateField should store
        a Python datetime.date, not a datetime.datetime"""
        b = RumBaba.objects.create()
        # Verify we didn't break DateTimeField behavior
        self.assertTrue(isinstance(b.baked_timestamp, datetime.datetime))
        # We need to test this this way because datetime.datetime inherits
        # from datetime.date:
        self.assertTrue(isinstance(b.baked_date, datetime.date) and not isinstance(b.baked_date, datetime.datetime))
