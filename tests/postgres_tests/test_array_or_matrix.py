from django.db.utils import DataError

from . import PostgreSQLTestCase
from .models import IntegerArrayOrMatrixModel


class TestArrayOrMatrixField(PostgreSQLTestCase):
    def test_validate_1d_array(self):
        instance = IntegerArrayOrMatrixModel(id=1, field=[1, 2, 3])
        instance.save()
        instance_from_db = IntegerArrayOrMatrixModel.objects.get(id=1)
        self.assertEqual(instance_from_db.field, [1, 2, 3])

    def test_validate_2d_array(self):
        instance = IntegerArrayOrMatrixModel(id=1, field=[[1, 2], [3, 4]])
        instance.save()
        instance_from_db = IntegerArrayOrMatrixModel.objects.get(id=1)
        self.assertEqual(instance_from_db.field, [[1, 2], [3, 4]])

    def test_validate_invalid_1d_array(self):
        instance = IntegerArrayOrMatrixModel(id=1, field=[1, 2, "a"])
        with self.assertRaises(DataError):
            instance.save()

    def test_validate_invalid_2d_array(self):
        instance = IntegerArrayOrMatrixModel(id=1, field=[[1, 2], ["a", 4]])
        with self.assertRaises(DataError):
            instance.save()
