from __future__ import unicode_literals

from django.contrib.localflavor.gb.forms import (
    GBPostcodeField, GBPhoneNumberField
)

from django.test import SimpleTestCase


class GBLocalFlavorTests(SimpleTestCase):
    def test_GBPostcodeField(self):
        error_invalid = ['Enter a valid postcode.']
        valid = {
            'BT32 4PX': 'BT32 4PX',
            'GIR 0AA': 'GIR 0AA',
            'BT324PX': 'BT32 4PX',
            ' so11aa ': 'SO1 1AA',
            ' so1  1aa ': 'SO1 1AA',
            'G2 3wt': 'G2 3WT',
            'EC1A 1BB': 'EC1A 1BB',
            'Ec1a1BB': 'EC1A 1BB',
        }
        invalid = {
            '1NV 4L1D': error_invalid,
            '1NV4L1D': error_invalid,
            ' b0gUS': error_invalid,
        }
        self.assertFieldOutput(GBPostcodeField, valid, invalid)
        valid = {}
        invalid = {
            '1NV 4L1D': ['Enter a bloody postcode!'],
        }
        kwargs = {'error_messages': {'invalid': 'Enter a bloody postcode!'}}
        self.assertFieldOutput(GBPostcodeField, valid, invalid, field_kwargs=kwargs)

    def test_GBPhoneNumberField(self):
        error_format = ['Phone numbers must be in +XXXXXXXXXXX format.']
        valid = {
            '020 3000 5555': '+442030005555',
            '(020) 3000 5555': '+442030005555',
            '+44 20 3000 5555': '+442030005555',
            '0203 000 5555': '+442030005555',
            '(0203) 000 5555': '+442030005555',
            '02030 005 555': '+442030005555',
            '+44 (0) 20 3000 5555': '+442030005555',
            '+44(0)203 000 5555': '+442030005555',
            '00 (44) 2030 005 555': '+442030005555',
            '(+44 203) 000 5555': '+442030005555',
            '(+44) 203 000 5555': '+442030005555',
            '011 44 203 000 5555': '+442030005555',
            '020-3000-5555': '+442030005555',
            '(020)-3000-5555': '+442030005555',
            '+44-20-3000-5555': '+442030005555',
            '0203-000-5555': '+442030005555',
            '(0203)-000-5555': '+442030005555',
            '02030-005-555': '+442030005555',
            '+44-(0)-20-3000-5555': '+442030005555',
            '+44(0)203-000-5555': '+442030005555',
            '00-(44)-2030-005-555': '+442030005555',
            '(+44-203)-000-5555': '+442030005555',
            '(+44)-203-000-5555': '+442030005555',
            '011-44-203-000-5555': '+442030005555'
        }
        invalid = {
            '011 44 203 000 5555 5': error_format,
            '+44 20 300 5555': error_format,
        }
        self.assertFieldOutput(GBPhoneNumberField, valid, invalid)
