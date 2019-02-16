from datetime import date

from . import PostgreSQLTestCase
from .models import (
    HStoreModel, IntegerArrayModel, JSONModel, NestedIntegerArrayModel,
    NullableIntegerArrayModel, OtherTypesArrayModel, RangesModel,
)

try:
    from psycopg2.extras import NumericRange, DateRange
except ImportError:
    pass  # psycopg2 isn't installed.


class BulkCreateTests(PostgreSQLTestCase):
    def test_bulk_create_to_set_pk_when_ignore_conflicts(self):
        test_data = [
            (IntegerArrayModel, 'field', [], [1, 2, 3]),
            (NullableIntegerArrayModel, 'field', [1, 2, 3], None),
            (JSONModel, 'field', {'a': 'b'}, {'c': 'd'}),
            (NestedIntegerArrayModel, 'field', [], [[1, 2, 3]]),
            (HStoreModel, 'field', {}, {1: 2}),
            (RangesModel, 'ints', None, NumericRange(lower=1, upper=10)),
            (RangesModel, 'dates', None, DateRange(lower=date.today(), upper=date.today())),
            (OtherTypesArrayModel, 'ips', [], ['1.2.3.4']),
            (OtherTypesArrayModel, 'json', [], [{'a': 'b'}])
        ]
        for Model, field, initial, new in test_data:
            with self.subTest(model=Model, field=field):
                objs = (Model(**{field: initial}) for _ in range(20))
                instances = Model.objects.bulk_create(objs, ignore_conflicts=True)
                for instance in instances:
                    self.assertIsNotNone(instance.pk)
