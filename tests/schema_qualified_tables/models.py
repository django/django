from django.db import models


class BillingCustomer(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "schema_qualified_tables"
        db_table = models.SchemaQualifiedTable("customer", schema="billing")
        managed = False


class BillingInvoice(models.Model):
    customer = models.ForeignKey(BillingCustomer, models.CASCADE)
    reference = models.CharField(max_length=100)

    class Meta:
        app_label = "schema_qualified_tables"
        db_table = models.SchemaQualifiedTable("invoice", schema="billing")
        managed = False


class SalesCustomer(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "schema_qualified_tables"
        db_table = models.SchemaQualifiedTable("customer", schema="sales")
        managed = False
