from unittest import mock

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, models
from django.db.models.constraints import BaseConstraint
from django.db.transaction import atomic
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature

from .models import (
    ChildModel, Product, UniqueConstraintConditionProduct,
    UniqueConstraintDeferrable, UniqueConstraintInclude,
    UniqueConstraintProduct,
)


def get_constraints(table):
    with connection.cursor() as cursor:
        return connection.introspection.get_constraints(cursor, table)


class BaseConstraintTests(SimpleTestCase):
    def test_constraint_sql(self):
        c = BaseConstraint('name')
        msg = 'This method must be implemented by a subclass.'
        with self.assertRaisesMessage(NotImplementedError, msg):
            c.constraint_sql(None, None)

    def test_create_sql(self):
        c = BaseConstraint('name')
        msg = 'This method must be implemented by a subclass.'
        with self.assertRaisesMessage(NotImplementedError, msg):
            c.create_sql(None, None)

    def test_remove_sql(self):
        c = BaseConstraint('name')
        msg = 'This method must be implemented by a subclass.'
        with self.assertRaisesMessage(NotImplementedError, msg):
            c.remove_sql(None, None)


class CheckConstraintTests(TestCase):
    def test_eq(self):
        check1 = models.Q(price__gt=models.F('discounted_price'))
        check2 = models.Q(price__lt=models.F('discounted_price'))
        self.assertEqual(
            models.CheckConstraint(check=check1, name='price'),
            models.CheckConstraint(check=check1, name='price'),
        )
        self.assertEqual(models.CheckConstraint(check=check1, name='price'), mock.ANY)
        self.assertNotEqual(
            models.CheckConstraint(check=check1, name='price'),
            models.CheckConstraint(check=check1, name='price2'),
        )
        self.assertNotEqual(
            models.CheckConstraint(check=check1, name='price'),
            models.CheckConstraint(check=check2, name='price'),
        )
        self.assertNotEqual(models.CheckConstraint(check=check1, name='price'), 1)

    def test_repr(self):
        check = models.Q(price__gt=models.F('discounted_price'))
        name = 'price_gt_discounted_price'
        constraint = models.CheckConstraint(check=check, name=name)
        self.assertEqual(
            repr(constraint),
            "<CheckConstraint: check='{}' name='{}'>".format(check, name),
        )

    def test_invalid_check_types(self):
        msg = (
            'CheckConstraint.check must be a Q instance or boolean expression.'
        )
        with self.assertRaisesMessage(TypeError, msg):
            models.CheckConstraint(check=models.F('discounted_price'), name='check')

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
        Product.objects.create(price=10, discounted_price=5)
        with self.assertRaises(IntegrityError):
            Product.objects.create(price=10, discounted_price=20)

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_database_constraint_unicode(self):
        Product.objects.create(price=10, discounted_price=5, unit='μg/mL')
        with self.assertRaises(IntegrityError):
            Product.objects.create(price=10, discounted_price=7, unit='l')

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_database_constraint_expression(self):
        Product.objects.create(price=999, discounted_price=5)
        with self.assertRaises(IntegrityError):
            Product.objects.create(price=1000, discounted_price=5)

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_database_constraint_expressionwrapper(self):
        Product.objects.create(price=499, discounted_price=5)
        with self.assertRaises(IntegrityError):
            Product.objects.create(price=500, discounted_price=5)

    @skipUnlessDBFeature('supports_table_check_constraints', 'can_introspect_check_constraints')
    def test_name(self):
        constraints = get_constraints(Product._meta.db_table)
        for expected_name in (
            'price_gt_discounted_price',
            'constraints_price_lt_1000_raw',
            'constraints_price_neq_500_wrap',
            'constraints_product_price_gt_0',
        ):
            with self.subTest(expected_name):
                self.assertIn(expected_name, constraints)

    @skipUnlessDBFeature('supports_table_check_constraints', 'can_introspect_check_constraints')
    def test_abstract_name(self):
        constraints = get_constraints(ChildModel._meta.db_table)
        self.assertIn('constraints_childmodel_adult', constraints)


class UniqueConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.p1, cls.p2 = UniqueConstraintProduct.objects.bulk_create([
            UniqueConstraintProduct(name='p1', color='red'),
            UniqueConstraintProduct(name='p2'),
        ])

    def test_eq(self):
        self.assertEqual(
            models.UniqueConstraint(fields=['foo', 'bar'], name='unique'),
            models.UniqueConstraint(fields=['foo', 'bar'], name='unique'),
        )
        self.assertEqual(
            models.UniqueConstraint(fields=['foo', 'bar'], name='unique'),
            mock.ANY,
        )
        self.assertNotEqual(
            models.UniqueConstraint(fields=['foo', 'bar'], name='unique'),
            models.UniqueConstraint(fields=['foo', 'bar'], name='unique2'),
        )
        self.assertNotEqual(
            models.UniqueConstraint(fields=['foo', 'bar'], name='unique'),
            models.UniqueConstraint(fields=['foo', 'baz'], name='unique'),
        )
        self.assertNotEqual(models.UniqueConstraint(fields=['foo', 'bar'], name='unique'), 1)

    def test_eq_with_condition(self):
        self.assertEqual(
            models.UniqueConstraint(
                fields=['foo', 'bar'], name='unique',
                condition=models.Q(foo=models.F('bar'))
            ),
            models.UniqueConstraint(
                fields=['foo', 'bar'], name='unique',
                condition=models.Q(foo=models.F('bar'))),
        )
        self.assertNotEqual(
            models.UniqueConstraint(
                fields=['foo', 'bar'],
                name='unique',
                condition=models.Q(foo=models.F('bar'))
            ),
            models.UniqueConstraint(
                fields=['foo', 'bar'],
                name='unique',
                condition=models.Q(foo=models.F('baz'))
            ),
        )

    def test_eq_with_deferrable(self):
        constraint_1 = models.UniqueConstraint(
            fields=['foo', 'bar'],
            name='unique',
            deferrable=models.Deferrable.DEFERRED,
        )
        constraint_2 = models.UniqueConstraint(
            fields=['foo', 'bar'],
            name='unique',
            deferrable=models.Deferrable.IMMEDIATE,
        )
        self.assertEqual(constraint_1, constraint_1)
        self.assertNotEqual(constraint_1, constraint_2)

    def test_eq_with_include(self):
        constraint_1 = models.UniqueConstraint(
            fields=['foo', 'bar'],
            name='include',
            include=['baz_1'],
        )
        constraint_2 = models.UniqueConstraint(
            fields=['foo', 'bar'],
            name='include',
            include=['baz_2'],
        )
        self.assertEqual(constraint_1, constraint_1)
        self.assertNotEqual(constraint_1, constraint_2)

    def test_eq_with_opclasses(self):
        constraint_1 = models.UniqueConstraint(
            fields=['foo', 'bar'],
            name='opclasses',
            opclasses=['text_pattern_ops', 'varchar_pattern_ops'],
        )
        constraint_2 = models.UniqueConstraint(
            fields=['foo', 'bar'],
            name='opclasses',
            opclasses=['varchar_pattern_ops', 'text_pattern_ops'],
        )
        self.assertEqual(constraint_1, constraint_1)
        self.assertNotEqual(constraint_1, constraint_2)

    def test_repr(self):
        fields = ['foo', 'bar']
        name = 'unique_fields'
        constraint = models.UniqueConstraint(fields=fields, name=name)
        self.assertEqual(
            repr(constraint),
            "<UniqueConstraint: fields=('foo', 'bar') name='unique_fields'>",
        )

    def test_repr_with_condition(self):
        constraint = models.UniqueConstraint(
            fields=['foo', 'bar'],
            name='unique_fields',
            condition=models.Q(foo=models.F('bar')),
        )
        self.assertEqual(
            repr(constraint),
            "<UniqueConstraint: fields=('foo', 'bar') name='unique_fields' "
            "condition=(AND: ('foo', F(bar)))>",
        )

    def test_repr_with_deferrable(self):
        constraint = models.UniqueConstraint(
            fields=['foo', 'bar'],
            name='unique_fields',
            deferrable=models.Deferrable.IMMEDIATE,
        )
        self.assertEqual(
            repr(constraint),
            "<UniqueConstraint: fields=('foo', 'bar') name='unique_fields' "
            "deferrable=Deferrable.IMMEDIATE>",
        )

    def test_repr_with_include(self):
        constraint = models.UniqueConstraint(
            fields=['foo', 'bar'],
            name='include_fields',
            include=['baz_1', 'baz_2'],
        )
        self.assertEqual(
            repr(constraint),
            "<UniqueConstraint: fields=('foo', 'bar') name='include_fields' "
            "include=('baz_1', 'baz_2')>",
        )

    def test_repr_with_opclasses(self):
        constraint = models.UniqueConstraint(
            fields=['foo', 'bar'],
            name='opclasses_fields',
            opclasses=['text_pattern_ops', 'varchar_pattern_ops'],
        )
        self.assertEqual(
            repr(constraint),
            "<UniqueConstraint: fields=('foo', 'bar') name='opclasses_fields' "
            "opclasses=['text_pattern_ops', 'varchar_pattern_ops']>",
        )

    def test_deconstruction(self):
        fields = ['foo', 'bar']
        name = 'unique_fields'
        constraint = models.UniqueConstraint(fields=fields, name=name)
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(path, 'django.db.models.UniqueConstraint')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'fields': tuple(fields), 'name': name})

    def test_deconstruction_with_condition(self):
        fields = ['foo', 'bar']
        name = 'unique_fields'
        condition = models.Q(foo=models.F('bar'))
        constraint = models.UniqueConstraint(fields=fields, name=name, condition=condition)
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(path, 'django.db.models.UniqueConstraint')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'fields': tuple(fields), 'name': name, 'condition': condition})

    def test_deconstruction_with_deferrable(self):
        fields = ['foo']
        name = 'unique_fields'
        constraint = models.UniqueConstraint(
            fields=fields,
            name=name,
            deferrable=models.Deferrable.DEFERRED,
        )
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(path, 'django.db.models.UniqueConstraint')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {
            'fields': tuple(fields),
            'name': name,
            'deferrable': models.Deferrable.DEFERRED,
        })

    def test_deconstruction_with_include(self):
        fields = ['foo', 'bar']
        name = 'unique_fields'
        include = ['baz_1', 'baz_2']
        constraint = models.UniqueConstraint(fields=fields, name=name, include=include)
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(path, 'django.db.models.UniqueConstraint')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {
            'fields': tuple(fields),
            'name': name,
            'include': tuple(include),
        })

    def test_deconstruction_with_opclasses(self):
        fields = ['foo', 'bar']
        name = 'unique_fields'
        opclasses = ['varchar_pattern_ops', 'text_pattern_ops']
        constraint = models.UniqueConstraint(fields=fields, name=name, opclasses=opclasses)
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(path, 'django.db.models.UniqueConstraint')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {
            'fields': tuple(fields),
            'name': name,
            'opclasses': opclasses,
        })

    def test_database_constraint(self):
        with self.assertRaises(IntegrityError):
            UniqueConstraintProduct.objects.create(name=self.p1.name, color=self.p1.color)

    @skipUnlessDBFeature('supports_partial_indexes')
    def test_database_constraint_with_condition(self):
        UniqueConstraintConditionProduct.objects.create(name='p1')
        UniqueConstraintConditionProduct.objects.create(name='p2')
        with self.assertRaises(IntegrityError):
            UniqueConstraintConditionProduct.objects.create(name='p1')

    def test_model_validation(self):
        msg = 'Unique constraint product with this Name and Color already exists.'
        with self.assertRaisesMessage(ValidationError, msg):
            UniqueConstraintProduct(name=self.p1.name, color=self.p1.color).validate_unique()

    @skipUnlessDBFeature('supports_partial_indexes')
    def test_model_validation_with_condition(self):
        """Partial unique constraints are ignored by Model.validate_unique()."""
        obj1 = UniqueConstraintConditionProduct.objects.create(name='p1', color='red')
        obj2 = UniqueConstraintConditionProduct.objects.create(name='p2')
        UniqueConstraintConditionProduct(name=obj1.name, color='blue').validate_unique()
        UniqueConstraintConditionProduct(name=obj2.name).validate_unique()

    def test_name(self):
        constraints = get_constraints(UniqueConstraintProduct._meta.db_table)
        expected_name = 'name_color_uniq'
        self.assertIn(expected_name, constraints)

    def test_condition_must_be_q(self):
        with self.assertRaisesMessage(ValueError, 'UniqueConstraint.condition must be a Q instance.'):
            models.UniqueConstraint(name='uniq', fields=['name'], condition='invalid')

    @skipUnlessDBFeature('supports_deferrable_unique_constraints')
    def test_initially_deferred_database_constraint(self):
        obj_1 = UniqueConstraintDeferrable.objects.create(name='p1', shelf='front')
        obj_2 = UniqueConstraintDeferrable.objects.create(name='p2', shelf='back')

        def swap():
            obj_1.name, obj_2.name = obj_2.name, obj_1.name
            obj_1.save()
            obj_2.save()

        swap()
        # Behavior can be changed with SET CONSTRAINTS.
        with self.assertRaises(IntegrityError):
            with atomic(), connection.cursor() as cursor:
                constraint_name = connection.ops.quote_name('name_init_deferred_uniq')
                cursor.execute('SET CONSTRAINTS %s IMMEDIATE' % constraint_name)
                swap()

    @skipUnlessDBFeature('supports_deferrable_unique_constraints')
    def test_initially_immediate_database_constraint(self):
        obj_1 = UniqueConstraintDeferrable.objects.create(name='p1', shelf='front')
        obj_2 = UniqueConstraintDeferrable.objects.create(name='p2', shelf='back')
        obj_1.shelf, obj_2.shelf = obj_2.shelf, obj_1.shelf
        with self.assertRaises(IntegrityError), atomic():
            obj_1.save()
        # Behavior can be changed with SET CONSTRAINTS.
        with connection.cursor() as cursor:
            constraint_name = connection.ops.quote_name('sheld_init_immediate_uniq')
            cursor.execute('SET CONSTRAINTS %s DEFERRED' % constraint_name)
            obj_1.save()
            obj_2.save()

    def test_deferrable_with_condition(self):
        message = 'UniqueConstraint with conditions cannot be deferred.'
        with self.assertRaisesMessage(ValueError, message):
            models.UniqueConstraint(
                fields=['name'],
                name='name_without_color_unique',
                condition=models.Q(color__isnull=True),
                deferrable=models.Deferrable.DEFERRED,
            )

    def test_deferrable_with_include(self):
        message = 'UniqueConstraint with include fields cannot be deferred.'
        with self.assertRaisesMessage(ValueError, message):
            models.UniqueConstraint(
                fields=['name'],
                name='name_inc_color_color_unique',
                include=['color'],
                deferrable=models.Deferrable.DEFERRED,
            )

    def test_deferrable_with_opclasses(self):
        message = 'UniqueConstraint with opclasses cannot be deferred.'
        with self.assertRaisesMessage(ValueError, message):
            models.UniqueConstraint(
                fields=['name'],
                name='name_text_pattern_ops_unique',
                opclasses=['text_pattern_ops'],
                deferrable=models.Deferrable.DEFERRED,
            )

    def test_invalid_defer_argument(self):
        message = 'UniqueConstraint.deferrable must be a Deferrable instance.'
        with self.assertRaisesMessage(ValueError, message):
            models.UniqueConstraint(
                fields=['name'],
                name='name_invalid',
                deferrable='invalid',
            )

    @skipUnlessDBFeature(
        'supports_table_check_constraints',
        'supports_covering_indexes',
    )
    def test_include_database_constraint(self):
        UniqueConstraintInclude.objects.create(name='p1', color='red')
        with self.assertRaises(IntegrityError):
            UniqueConstraintInclude.objects.create(name='p1', color='blue')

    def test_invalid_include_argument(self):
        msg = 'UniqueConstraint.include must be a list or tuple.'
        with self.assertRaisesMessage(ValueError, msg):
            models.UniqueConstraint(
                name='uniq_include',
                fields=['field'],
                include='other',
            )

    def test_invalid_opclasses_argument(self):
        msg = 'UniqueConstraint.opclasses must be a list or tuple.'
        with self.assertRaisesMessage(ValueError, msg):
            models.UniqueConstraint(
                name='uniq_opclasses',
                fields=['field'],
                opclasses='jsonb_path_ops',
            )

    def test_opclasses_and_fields_same_length(self):
        msg = (
            'UniqueConstraint.fields and UniqueConstraint.opclasses must have '
            'the same number of elements.'
        )
        with self.assertRaisesMessage(ValueError, msg):
            models.UniqueConstraint(
                name='uniq_opclasses',
                fields=['field'],
                opclasses=['foo', 'bar'],
            )
