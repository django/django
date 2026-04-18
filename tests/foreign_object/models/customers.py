from django.db import models


class Address(models.Model):
    company = models.CharField(max_length=1)
    customer_id = models.IntegerField()

    class Meta:
        unique_together = [
            ("company", "customer_id"),
        ]


class Customer(models.Model):
    company = models.CharField(max_length=1)
    customer_id = models.IntegerField()
    address = models.ForeignObject(
        Address,
        models.CASCADE,
        null=True,
        # order mismatches the Contact ForeignObject.
        from_fields=["company", "customer_id"],
        to_fields=["company", "customer_id"],
    )

    class Meta:
        unique_together = [
            ("company", "customer_id"),
        ]


class Contact(models.Model):
    company_code = models.CharField(max_length=1)
    customer_code = models.IntegerField()
    customer = models.ForeignObject(
        Customer,
        models.CASCADE,
        related_name="contacts",
        to_fields=["customer_id", "company"],
        from_fields=["customer_code", "company_code"],
    )


class CustomerTab(models.Model):
    customer_id = models.IntegerField()
    customer = models.ForeignObject(
        Customer,
        from_fields=["customer_id"],
        to_fields=["id"],
        on_delete=models.CASCADE,
    )

    class Meta:
        required_db_features = {"supports_table_check_constraints"}
        constraints = [
            models.CheckConstraint(
                condition=models.Q(customer__lt=1000),
                name="customer_id_limit",
            ),
        ]
