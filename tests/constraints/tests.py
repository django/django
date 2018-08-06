from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.test import TestCase, skipUnlessDBFeature

from .models import Product


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


class UniqueConstraintCheck(TestCase):
    @classmethod
    def setUpTestData(cls):
        Product.objects.create(name='Valid')

    def test_repr(self):
        fields = ['foo', 'bar']
        name = 'unique_fields'
        constraint = models.UniqueConstraint(fields=fields, name=name)
        self.assertEqual(
            repr(constraint),
            "<UniqueConstraint: fields=('foo', 'bar') name='unique_fields'>",
        )

    def test_deconstruction(self):
        fields = ['foo', 'bar']
        name = 'unique_fields'
        check = models.UniqueConstraint(fields=fields, name=name)
        path, args, kwargs = check.deconstruct()
        self.assertEqual(path, 'django.db.models.UniqueConstraint')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'fields': tuple(fields), 'name': name})

    def test_database_constraint(self):
        with self.assertRaises(IntegrityError):
            Product.objects.create(name='Valid')

    def test_model_validation(self):
        with self.assertRaisesMessage(ValidationError, 'Product with this Name already exists.'):
            Product(name='Valid').validate_unique()
