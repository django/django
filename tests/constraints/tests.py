from django.db import IntegrityError, models
from django.test import TestCase, skipUnlessDBFeature

from .models import Product


class CheckConstraintTests(TestCase):
    def test_repr(self):
        constraint = models.Q(price__gt=models.F('discounted_price'))
        name = 'price_gt_discounted_price'
        check = models.CheckConstraint(constraint, name)
        self.assertEqual(
            repr(check),
            "<CheckConstraint: constraint='{}' name='{}'>".format(constraint, name),
        )

    def test_deconstruction(self):
        constraint = models.Q(price__gt=models.F('discounted_price'))
        name = 'price_gt_discounted_price'
        check = models.CheckConstraint(constraint, name)
        path, args, kwargs = check.deconstruct()
        self.assertEqual(path, 'django.db.models.CheckConstraint')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'constraint': constraint, 'name': name})

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_model_constraint(self):
        Product.objects.create(name='Valid', price=10, discounted_price=5)
        with self.assertRaises(IntegrityError):
            Product.objects.create(name='Invalid', price=10, discounted_price=20)
