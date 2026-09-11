from ipaddress import IPv4Address, IPv6Address

from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase

from .models import GenericIPAddress


class GenericIPAddressFieldTests(TestCase):
    def test_genericipaddressfield_formfield_protocol(self):
        """
        GenericIPAddressField with a specified protocol does not generate a
        formfield without a protocol.
        """
        model_field = models.GenericIPAddressField(protocol="IPv4")
        form_field = model_field.formfield()
        with self.assertRaises(ValidationError):
            form_field.clean("::1")
        model_field = models.GenericIPAddressField(protocol="IPv6")
        form_field = model_field.formfield()
        with self.assertRaises(ValidationError):
            form_field.clean("127.0.0.1")

    def test_null_value(self):
        """
        Null values should be resolved to None.
        """
        GenericIPAddress.objects.create()
        o = GenericIPAddress.objects.get()
        self.assertIsNone(o.ip)

    def test_blank_string_saved_as_null(self):
        o = GenericIPAddress.objects.create(ip="")
        o.refresh_from_db()
        self.assertIsNone(o.ip)
        GenericIPAddress.objects.update(ip="")
        o.refresh_from_db()
        self.assertIsNone(o.ip)

    def test_save_load(self):
        instance = GenericIPAddress.objects.create(ip="::1")
        loaded = GenericIPAddress.objects.get()
        self.assertEqual(loaded.ip, instance.ip)

    def test_save_load_ipaddress(self):
        """
        Inserts, updates, and lookups accept ipaddress objects.
        """
        instance = GenericIPAddress.objects.create(ip=IPv4Address("192.0.2.1"))
        instance.refresh_from_db()
        self.assertEqual(instance.ip, "192.0.2.1")

        instance.ip = IPv4Address("192.0.2.2")
        instance.save()
        instance.refresh_from_db()
        self.assertEqual(instance.ip, "192.0.2.2")

        GenericIPAddress.objects.update(ip=IPv4Address("192.0.2.3"))
        self.assertSequenceEqual(
            GenericIPAddress.objects.filter(ip=IPv4Address("192.0.2.3")), [instance]
        )

    def test_get_prep_value_ipaddress(self):
        field = models.GenericIPAddressField()
        tests = [
            (IPv4Address("192.0.2.1"), "192.0.2.1"),
            (IPv6Address("::ffff:192.0.2.1"), "::ffff:192.0.2.1"),
        ]
        for value, expected in tests:
            with self.subTest(value=value):
                self.assertEqual(field.get_prep_value(value), expected)
