from django.core.exceptions import ValidationError
from django.test import TestCase, skipUnlessDBFeature

from .models import (
    ChildProduct,
    ChildUniqueConstraintProduct,
    Product,
    UniqueConstraintConditionProduct,
    UniqueConstraintNullsDistinctProduct,
    UniqueConstraintProduct,
)


class PerformConstraintChecksTest(TestCase):
    @skipUnlessDBFeature("supports_table_check_constraints")
    def test_full_clean_with_check_constraints(self):
        product = Product(price=10, discounted_price=15)
        with self.assertRaises(ValidationError) as cm:
            product.full_clean()
        self.assertEqual(
            cm.exception.message_dict,
            {
                "__all__": [
                    "Constraint “price_gt_discounted_price_validation” is violated."
                ]
            },
        )

    @skipUnlessDBFeature("supports_table_check_constraints")
    def test_full_clean_with_check_constraints_on_child_model(self):
        product = ChildProduct(price=10, discounted_price=15)
        with self.assertRaises(ValidationError) as cm:
            product.full_clean()
        self.assertEqual(
            cm.exception.message_dict,
            {
                "__all__": [
                    "Constraint “price_gt_discounted_price_validation” is violated."
                ]
            },
        )

    @skipUnlessDBFeature("supports_table_check_constraints")
    def test_full_clean_with_check_constraints_disabled(self):
        product = Product(price=10, discounted_price=15)
        product.full_clean(validate_constraints=False)

    def test_full_clean_with_unique_constraints(self):
        UniqueConstraintProduct.objects.create(name="product", color="yellow", rank=1)
        tests = [
            UniqueConstraintProduct(name="product", color="yellow", rank=1),
            # Child model.
            ChildUniqueConstraintProduct(name="product", color="yellow", rank=1),
        ]
        for product in tests:
            with self.subTest(model=product.__class__.__name__):
                with self.assertRaises(ValidationError) as cm:
                    product.full_clean()
                self.assertEqual(
                    cm.exception.message_dict,
                    {
                        "__all__": [
                            "Unique constraint product with this Name and Color "
                            "already exists."
                        ],
                        "rank": [
                            "Unique constraint product with this Rank already exists."
                        ],
                    },
                )

    def test_full_clean_with_unique_constraints_disabled(self):
        UniqueConstraintProduct.objects.create(name="product", color="yellow", rank=1)
        product = UniqueConstraintProduct(name="product", color="yellow", rank=1)
        product.full_clean(validate_constraints=False)

    @skipUnlessDBFeature("supports_partial_indexes")
    def test_full_clean_with_partial_unique_constraints(self):
        UniqueConstraintConditionProduct.objects.create(name="product")
        product = UniqueConstraintConditionProduct(name="product")
        with self.assertRaises(ValidationError) as cm:
            product.full_clean()
        self.assertEqual(
            cm.exception.message_dict,
            {
                "__all__": [
                    "Constraint “name_without_color_uniq_validation” is violated."
                ]
            },
        )

    @skipUnlessDBFeature("supports_partial_indexes")
    def test_full_clean_with_partial_unique_constraints_disabled(self):
        UniqueConstraintConditionProduct.objects.create(name="product")
        product = UniqueConstraintConditionProduct(name="product")
        product.full_clean(validate_constraints=False)

    @skipUnlessDBFeature("supports_nulls_distinct_unique_constraints")
    def test_full_clean_with_nulls_distinct_unique_constraints(self):
        UniqueConstraintNullsDistinctProduct.objects.create(name=None)
        product = UniqueConstraintNullsDistinctProduct(name=None)
        with self.assertRaises(ValidationError) as cm:
            product.full_clean()
        self.assertEqual(
            cm.exception.message_dict,
            {
                "name": [
                    "Unique constraint nulls distinct product with this Name "
                    "already exists."
                ]
            },
        )

    @skipUnlessDBFeature("supports_nulls_distinct_unique_constraints")
    def test_full_clean_with_nulls_distinct_unique_constraints_disabled(self):
        UniqueConstraintNullsDistinctProduct.objects.create(name=None)
        product = UniqueConstraintNullsDistinctProduct(name=None)
        product.full_clean(validate_constraints=False)
