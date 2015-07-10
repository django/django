from __future__ import unicode_literals

import unittest

from .models import PersonWithCustomMaxLengths, PersonWithDefaultMaxLengths


class MaxLengthArgumentsTests(unittest.TestCase):

    def verify_max_length(self, model, field, length):
        self.assertEqual(model._meta.get_field(field).max_length, length)

    def test_default_max_lengths(self):
        self.verify_max_length(PersonWithDefaultMaxLengths, 'email', 254)
        self.verify_max_length(PersonWithDefaultMaxLengths, 'vcard', 100)
        self.verify_max_length(PersonWithDefaultMaxLengths, 'homepage', 200)
        self.verify_max_length(PersonWithDefaultMaxLengths, 'avatar', 100)

    def test_custom_max_lengths(self):
        self.verify_max_length(PersonWithCustomMaxLengths, 'email', 250)
        self.verify_max_length(PersonWithCustomMaxLengths, 'vcard', 250)
        self.verify_max_length(PersonWithCustomMaxLengths, 'homepage', 250)
        self.verify_max_length(PersonWithCustomMaxLengths, 'avatar', 250)


class MaxLengthORMTests(unittest.TestCase):

    def test_custom_max_lengths(self):
        args = {
            "email": "someone@example.com",
            "vcard": "vcard",
            "homepage": "http://example.com/",
            "avatar": "me.jpg"
        }

        for field in ("email", "vcard", "homepage", "avatar"):
            new_args = args.copy()
            new_args[field] = "X" * 250  # a value longer than any of the default fields could hold.
            p = PersonWithCustomMaxLengths.objects.create(**new_args)
            self.assertEqual(getattr(p, field), ("X" * 250))
