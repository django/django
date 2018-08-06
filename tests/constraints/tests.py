from django.db import IntegrityError, connection, models
from django.db.models.constraints import BaseConstraint
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature

from .models import Product


def get_constraints(table):
    with connection.cursor() as cursor:
        return connection.introspection.get_constraints(cursor, table)


class BaseConstraintTests(SimpleTestCase):
    def test_constraint_sql(self):
        c = BaseConstraint('name')
        msg = 'This method must be implemented by a subclass.'
        with self.assertRaisesMessage(NotImplementedError, msg):
            c.constraint_sql(None, None)


class CheckConstraintTests(TestCase):
    def test_repr(self):
        check = models.Q(price__gt=models.F('discounted_price'))
        name = 'price_gt_discounted_price'
        constraint = models.CheckConstraint(check=check, name=name)
        self.assertEqual(
            repr(constraint),
            "<CheckConstraint: check='{}' name='{}'>".format(check, name),
        )

    def test_deconstruction(self):
        check = models.Q(price__gt=models.F('discounted_price'))
        name = 'price_gt_discounted_price'
        constraint = models.CheckConstraint(check=check, name=name)
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(path, 'django.db.models.CheckConstraint')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'check': check, 'name': name})

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_database_constraint(self):
        Product.objects.create(name='Valid', price=10, discounted_price=5)
        with self.assertRaises(IntegrityError):
            Product.objects.create(name='Invalid', price=10, discounted_price=20)

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_name(self):
        constraints = get_constraints(Product._meta.db_table)
        expected_name = 'price_gt_discounted_price'
        if connection.features.uppercases_column_names:
            expected_name = expected_name.upper()
        self.assertIn(expected_name, constraints)
