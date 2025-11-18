from django.core.exceptions import ValidationError
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
        self.assertIn(expected_name, constraints)

    def test_check_constraint_with_or_operator_sql(self):
        """
        Test that CheckConstraint with OR operator uses simple column names
        without table qualification. This prevents errors in SQLite when
        renaming tables during migrations.

        Regression test for #31331.
        """
        from django.db.backends.sqlite3.schema import DatabaseSchemaEditor

        check = models.Q(price__gt=10, discounted_price__isnull=False) | models.Q(price__lte=10)
        constraint = models.CheckConstraint(check=check, name='test_or_constraint')

        # Use a schema editor to generate SQL
        schema_editor = DatabaseSchemaEditor(connection)
        check_sql = constraint._get_check_sql(Product, schema_editor)

        # The SQL should NOT contain qualified table names like "constraints_product"."field"
        # This was a bug where AND clauses used Col (qualified) but OR clauses used SimpleCol
        self.assertNotIn('constraints_product', check_sql.lower())
        # Verify it contains the expected column references
        self.assertIn('price', check_sql.lower())
        self.assertIn('discounted_price', check_sql.lower())

    def test_check_constraint_nested_q_objects(self):
        """
        Test that CheckConstraint with nested Q objects uses simple column names.

        Regression test for #31331.
        """
        from django.db.backends.sqlite3.schema import DatabaseSchemaEditor

        # Complex nested Q objects with both AND and OR
        check = (
            models.Q(models.Q(price__gt=10, discounted_price__isnull=False) | models.Q(price__lte=5)) &
            models.Q(name__isnull=False)
        )
        constraint = models.CheckConstraint(check=check, name='test_nested_or_constraint')

        # Use a schema editor to generate SQL
        schema_editor = DatabaseSchemaEditor(connection)
        check_sql = constraint._get_check_sql(Product, schema_editor)

        # The SQL should NOT contain qualified table names
        self.assertNotIn('constraints_product', check_sql.lower())


class UniqueConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.p1, cls.p2 = Product.objects.bulk_create([
            Product(name='p1', color='red'),
            Product(name='p2'),
        ])

    def test_eq(self):
        self.assertEqual(
            models.UniqueConstraint(fields=['foo', 'bar'], name='unique'),
            models.UniqueConstraint(fields=['foo', 'bar'], name='unique'),
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

    def test_database_constraint(self):
        with self.assertRaises(IntegrityError):
            Product.objects.create(name=self.p1.name, color=self.p1.color)

    def test_model_validation(self):
        with self.assertRaisesMessage(ValidationError, 'Product with this Name and Color already exists.'):
            Product(name=self.p1.name, color=self.p1.color).validate_unique()

    def test_model_validation_with_condition(self):
        """Partial unique constraints are ignored by Model.validate_unique()."""
        Product(name=self.p1.name, color='blue').validate_unique()
        Product(name=self.p2.name).validate_unique()

    def test_name(self):
        constraints = get_constraints(Product._meta.db_table)
        expected_name = 'name_color_uniq'
        self.assertIn(expected_name, constraints)

    def test_condition_must_be_q(self):
        with self.assertRaisesMessage(ValueError, 'UniqueConstraint.condition must be a Q instance.'):
            models.UniqueConstraint(name='uniq', fields=['name'], condition='invalid')

    def test_unique_constraint_condition_with_or_operator_sql(self):
        """
        Test that UniqueConstraint condition with OR operator uses simple column names.

        Regression test for #31331.
        """
        from django.db.backends.sqlite3.schema import DatabaseSchemaEditor

        condition = models.Q(price__gt=10, discounted_price__isnull=False) | models.Q(price__lte=10)
        constraint = models.UniqueConstraint(fields=['name'], name='test_or_unique', condition=condition)

        # Use a schema editor to generate SQL
        schema_editor = DatabaseSchemaEditor(connection)
        condition_sql = constraint._get_condition_sql(Product, schema_editor)

        # The SQL should NOT contain qualified table names
        self.assertNotIn('constraints_product', condition_sql.lower())
        # Verify it contains the expected column references
        self.assertIn('price', condition_sql.lower())
        self.assertIn('discounted_price', condition_sql.lower())
