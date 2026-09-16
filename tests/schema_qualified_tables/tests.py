from unittest import mock

from django.db import NotSupportedError, connection, models
from django.db.migrations.writer import MigrationWriter
from django.db.models import sql
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.test.utils import isolate_apps

from .models import BillingCustomer, BillingInvoice, SalesCustomer


class SchemaQualifiedTableTests(TestCase):
    def set_schema_qualified_table_references_support(self, value):
        original = connection.features.supports_schema_qualified_table_references
        connection.features.supports_schema_qualified_table_references = value
        self.addCleanup(
            setattr,
            connection.features,
            "supports_schema_qualified_table_references",
            original,
        )

    def table_sql(self, model):
        return model._meta.db_table.as_sql_name(connection)

    def test_schema_qualified_table_renders_sql_name(self):
        self.set_schema_qualified_table_references_support(True)
        table = BillingCustomer._meta.db_table
        qn = connection.ops.quote_name

        self.assertEqual(
            table.as_sql_name(connection),
            "%s.%s" % (qn("billing"), qn("customer")),
        )

    def test_schema_qualified_table_requires_backend_support(self):
        self.set_schema_qualified_table_references_support(False)

        table = BillingCustomer._meta.db_table

        with self.assertRaisesMessage(
            NotSupportedError,
            "doesn't support schema-qualified table references",
        ):
            table.as_sql_name(connection)

    def test_select_uses_schema_qualified_table(self):
        self.set_schema_qualified_table_references_support(True)

        sql_string = str(BillingCustomer.objects.all().query)

        self.assertIn(self.table_sql(BillingCustomer), sql_string)

    def test_same_table_name_can_be_qualified_by_different_schemas(self):
        self.set_schema_qualified_table_references_support(True)

        billing_sql = str(BillingCustomer.objects.all().query)
        sales_sql = str(SalesCustomer.objects.all().query)

        self.assertIn(self.table_sql(BillingCustomer), billing_sql)
        self.assertIn(self.table_sql(SalesCustomer), sales_sql)

    def test_join_uses_schema_qualified_table(self):
        self.set_schema_qualified_table_references_support(True)

        sql_string = str(BillingInvoice.objects.select_related("customer").query)

        self.assertIn(self.table_sql(BillingInvoice), sql_string)
        self.assertIn(self.table_sql(BillingCustomer), sql_string)

    def test_insert_uses_schema_qualified_table(self):
        self.set_schema_qualified_table_references_support(True)
        query = sql.InsertQuery(BillingCustomer)
        query.insert_values(
            [BillingCustomer._meta.get_field("name")],
            [BillingCustomer(name="Acme")],
        )

        sql_string, params = query.get_compiler(connection=connection).as_sql()[0]

        self.assertIn(
            "INSERT INTO %s" % self.table_sql(BillingCustomer),
            sql_string,
        )
        self.assertEqual(params, ("Acme",))

    @skipUnlessDBFeature("supports_schema_qualified_table_references")
    def test_returning_columns_uses_schema_qualified_table(self):
        sql_string, params = connection.ops.returning_columns(
            [BillingCustomer._meta.pk]
        )

        self.assertIn(self.table_sql(BillingCustomer), sql_string)
        self.assertEqual(params, ())

    def test_update_uses_schema_qualified_table(self):
        self.set_schema_qualified_table_references_support(True)
        query = BillingCustomer.objects.all().query.chain(sql.UpdateQuery)
        query.add_update_values({"name": "Acme"})

        sql_string, params = query.get_compiler(connection=connection).as_sql()

        self.assertIn(
            "UPDATE %s %s SET"
            % (
                self.table_sql(BillingCustomer),
                connection.ops.quote_name("T1"),
            ),
            sql_string,
        )
        self.assertEqual(params, ("Acme",))

    def test_delete_uses_schema_qualified_table(self):
        self.set_schema_qualified_table_references_support(True)
        query = BillingCustomer.objects.filter(name="Acme").query.chain(sql.DeleteQuery)

        sql_string, params = query.get_compiler(connection=connection).as_sql()

        self.assertIn(
            "DELETE FROM %s %s"
            % (
                self.table_sql(BillingCustomer),
                connection.ops.quote_name("T1"),
            ),
            sql_string,
        )
        self.assertEqual(params, ("Acme",))

    def test_delete_batch_uses_schema_qualified_table(self):
        compiler_class = connection.ops.compiler("SQLDeleteCompiler")
        query = sql.DeleteQuery(BillingCustomer)

        with mock.patch.object(compiler_class, "execute_sql", return_value=1):
            deleted = query.delete_batch([1], connection.alias)

        self.assertEqual(deleted, 1)
        self.assertEqual(list(query.alias_map), [query.base_table])

    def test_schema_qualified_table_can_be_serialized_in_migrations(self):
        table = BillingCustomer._meta.db_table

        serialized, imports = MigrationWriter.serialize(table)

        self.assertEqual(
            serialized,
            "models.SchemaQualifiedTable('customer', schema='billing')",
        )
        self.assertEqual(imports, {"from django.db import models"})

    @isolate_apps("schema_qualified_tables")
    def test_schema_qualified_table_requires_unmanaged_model(self):
        class ManagedCustomer(models.Model):
            class Meta:
                app_label = "schema_qualified_tables"
                db_table = models.SchemaQualifiedTable(
                    "customer",
                    schema="billing",
                )

        errors = ManagedCustomer.check()

        self.assertEqual(errors[0].id, "models.E051")
        self.assertEqual(
            errors[0].msg,
            "'managed' must be False when 'db_table' is a SchemaQualifiedTable.",
        )


@skipUnlessDBFeature("supports_schema_qualified_table_references")
class SchemaQualifiedTableDatabaseTests(TransactionTestCase):
    available_apps = ["schema_qualified_tables"]

    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA billing")
            cursor.execute("CREATE SCHEMA sales")
            cursor.execute("""
                CREATE TABLE billing.customer (
                    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    name varchar(100) NOT NULL
                )
                """)
            cursor.execute("""
                CREATE TABLE billing.invoice (
                    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    customer_id integer NOT NULL REFERENCES billing.customer (id),
                    reference varchar(100) NOT NULL
                )
                """)
            cursor.execute("""
                CREATE TABLE sales.customer (
                    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    name varchar(100) NOT NULL
                )
                """)
        self.addCleanup(self.drop_schemas)

    def drop_schemas(self):
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA billing CASCADE")
            cursor.execute("DROP SCHEMA sales CASCADE")

    def test_crud_and_join(self):
        billing_customer = BillingCustomer.objects.create(name="Billing customer")
        sales_customer = SalesCustomer.objects.create(name="Sales customer")
        invoice = BillingInvoice.objects.create(
            customer=billing_customer,
            reference="INV-001",
        )

        invoice = BillingInvoice.objects.select_related("customer").get(pk=invoice.pk)
        self.assertEqual(
            invoice.customer,
            billing_customer,
        )
        self.assertEqual(
            SalesCustomer.objects.get(pk=sales_customer.pk),
            sales_customer,
        )
        self.assertEqual(
            BillingCustomer.objects.filter(pk=billing_customer.pk).update(
                name="Updated customer"
            ),
            1,
        )
        billing_customer.refresh_from_db()
        self.assertEqual(billing_customer.name, "Updated customer")
        self.assertEqual(
            BillingInvoice.objects.filter(pk=invoice.pk).delete()[0],
            1,
        )
