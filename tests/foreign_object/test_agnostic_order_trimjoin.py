#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import unicode_literals, print_function, absolute_import

from django.apps import apps
from django.conf import settings
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.models.deletion import CASCADE
from django.test.testcases import TestCase
from .models import Customer, Contact, PhoneNumber, Address



class TestLookupQuery(TestCase):
    fixtures = ["customers.json"]

    def test_forward_lookup(self):
        customer = Customer.objects.get(pk=1)
        self.assertEqual(1, Contact.objects.filter(customer=customer).count())
        self.assertEqual(1, Contact.objects.filter(customer__name="moiraine & cie").count())

    def test_backward_lookup(self):
        contact = Contact.objects.get(pk=1)  # moiraine
        self.assertEqual(1, Customer.objects.filter(contacts__surname=contact.surname).count())
        self.assertEqual(1, Customer.objects.filter(contacts=contact).count())

    def test_deep_forward(self):
        c = Customer.objects.get(pk=1)
        a = c.address
        self.assertEqual([c], list(Customer.objects.filter(address__in=[a])))

    def test_deep_backward(self):
        c = Customer.objects.get(pk=1)
        a = c.address
        l = list(Address.objects.filter(customer__in=[c]))
        self.assertEqual([a], l)

    def test_very_deep_mixed_forward(self):
        p = PhoneNumber.objects.get(pk=1)
        c = Contact.objects.get(pk=2)
        cu = Customer.objects.get(pk=1)
        a = Address.objects.get(pk=1)
        self.assertEqual([p], list(PhoneNumber.objects.filter(contact=c)))
        self.assertEqual([p], list(PhoneNumber.objects.filter(contact__customer=cu)))

    def test_very_deep_optimized_forward(self):
        # this query is optimized by django
        p = PhoneNumber.objects.get(pk=1)
        a = Address.objects.get(pk=1)
        q = PhoneNumber.objects.filter(contact__customer__address=a)
        self.assertEqual([p], list(q))

