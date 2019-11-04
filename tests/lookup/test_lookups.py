from datetime import datetime

from django.db.models import Value
from django.db.models.fields import DateTimeField
from django.db.models.lookups import YearComparisonLookup
from django.test import SimpleTestCase


class YearComparisonLookupTests(SimpleTestCase):
    def test_get_bound(self):
        look_up = YearComparisonLookup(
            lhs=Value(datetime(2010, 1, 1, 0, 0, 0), output_field=DateTimeField()),
            rhs=Value(datetime(2010, 1, 1, 23, 59, 59), output_field=DateTimeField()),
        )
        msg = 'subclasses of YearComparisonLookup must provide a get_bound() method'
        with self.assertRaisesMessage(NotImplementedError, msg):
            look_up.get_bound(datetime(2010, 1, 1, 0, 0, 0), datetime(2010, 1, 1, 23, 59, 59))
