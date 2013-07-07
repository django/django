# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django import forms
from django.test import TestCase


class PriceForm(forms.Form):
    price = forms.IntegerField()

    def clean_price(self, warn):
        p = self.cleaned_data['price']
        if p < 10:
            warn("That's an awfully low price")
        if p == 7:
            warn("7 is a pretty strange price")
        return p


class WarningTests(TestCase):
    def test_warnings(self):
        form = PriceForm({'price': 5})
        self.assertTrue(form.is_valid())
        self.assertFalse(form.is_valid(require_no_warnings=True))
        self.assertEqual(form.warnings, {
            'price': ["That's an awfully low price"]
        })
        form = PriceForm({'price': 7})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.warnings, {
            'price': ["That's an awfully low price",
                      "7 is a pretty strange price"]
        })
        self.assertHTMLEqual(form.as_p(), """
            <ul class="warninglist">
                <li>That&#39;s an awfully low price</li>
                <li>7 is a pretty strange price</li>
            </ul>
            <p>
                <label for="id_price">Price:</label>
                <input id="id_price" name="price" type="text" value="7" />
            </p>
        """)
