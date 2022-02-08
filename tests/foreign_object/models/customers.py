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
