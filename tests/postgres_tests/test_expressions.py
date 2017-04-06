from django.contrib.postgres.expressions import FilterAgg
from django.db.models import Q, Count

from . import PostgreSQLTestCase
from .test_json import skipUnlessPG94

try:
    from .models import FilterAggParentModel, FilterAggTestModel
except ImportError:
    pass


@skipUnlessPG94
class TestFilterAgg(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.parent_instance = FilterAggParentModel.objects.create()
        for x in range(4):
            FilterAggTestModel.objects.create(
                parent=cls.parent_instance,
                integer_field=x
            )
        FilterAggTestModel.objects.create(
            parent=cls.parent_instance,
            integer_field=1
        )

    def test_filter_agg(self):
        qset = FilterAggParentModel.objects.annotate(
            zero_count=FilterAgg(Count('filteraggtestmodel'), Q(filteraggtestmodel__integer_field=1)),
            child_count=Count('filteraggtestmodel'),
        )
        result = qset.first()
        self.assertEqual(result.child_count, 5)
        self.assertEqual(result.zero_count, 2)
