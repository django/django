from django.db.models import F, Sum
from django.db.models.sql import Query
from django.test import SimpleTestCase, TestCase

from .models import Annotation


class CustomGroupByTests(SimpleTestCase):

    # Although the tests are mainly relevant for OLAP functionality,
    # but not tied to a specific database backend
    def test_group_by_f(self):
        query = Query(model=Annotation)
        query.custom_group_by = True
        query.group(F('name'))
        self.assertEqual(query.get_group_by_cols(), (F('name'),))

    def test_group_by_expression(self):
        query = Query(model=Annotation)
        query.custom_group_by = True
        msg = (
            "The GROUP BY clause is handled already quite well by Django. Please use only "
            "this method in case you found a short-coming, e.g., grouping sets. You can use"
            "str(query) to evaluate if Django already translates the ORM query without the use"
            "of this method."
        )
        with self.assertWarnsMessage(UserWarning, msg):
            query.group(Sum('name'))
        self.assertEqual(query.get_group_by_cols(), (Sum('name'),))

    # test custom expressions that are not grouping sets or cube for the warning.

    def test_multiple_expressions(self):
        pass

    def test_grouping_sets(self):
        pass

    def test_exception(self):
        msg = 'custom_group_by requires that all expressions are either strings, F-objects or expressions'
        with self.assertRaisesMessage(ValueError, msg):
            query = Query(model=Annotation)
            query.custom_group_by = True
            query.group(object())


class OLAPFunctionTests(TestCase):

    # This needs to be filled in with meaningful data, to check that the
    # query
    pass
