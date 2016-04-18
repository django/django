#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import unicode_literals, print_function, absolute_import

from django.db.models.deletion import CASCADE
from django.db.models.fields.related import ForeignObject
from django.db import models

class Address(models.Model):
    company = models.CharField(max_length=1)
    tiers_id = models.IntegerField()
    city = models.CharField(max_length=255)
    postcode = models.CharField(max_length=32)

    class Meta(object):
        unique_together = [
            ("company", "tiers_id"),
        ]


class Customer(models.Model):
    company = models.CharField(max_length=1)
    customer_id = models.IntegerField()
    name = models.CharField(max_length=255)
    address = ForeignObject(
        Address, on_delete=CASCADE, null=True,
        from_fields=["customer_id", "company"],
        to_fields=["tiers_id", "company"]
    )

    class Meta(object):
        unique_together = [
            ("company", "customer_id"),
        ]

class Contact(models.Model):
    company_code = models.CharField(max_length=1)
    customer_code = models.IntegerField()
    surname = models.CharField(max_length=255)
    # virtual field
    customer = ForeignObject(
        Customer, on_delete=CASCADE, related_name='contacts',
        # not the same order as for Customer -> address which is (customer, company)
        to_fields=["company", "customer_id"],
        from_fields=["company_code", "customer_code"]
        # with same order as for Customer, the bug does not trigger
        # to_fields = ["customer_id", "company"],
        # from_fields = ["customer_code", "company_code"]
    )

class PhoneNumber(models.Model):
    num = models.CharField(max_length=32)
    type_number = models.IntegerField()
    contact = models.ForeignKey(Contact, on_delete=CASCADE, related_name='phonenumbers')