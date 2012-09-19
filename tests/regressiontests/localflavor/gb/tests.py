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
        valid = {
            '020 3000 5555': '+44 20 3000 5555',
            '(020) 3000 5555': '+44 20 3000 5555',
            '+44 20 3000 5555': '+44 20 3000 5555',
            '0203 000 5555': '+44 20 3000 5555',
            '(0203) 000 5555': '+44 20 3000 5555',
            '02030 005 555': '+44 20 3000 5555',
            '+44 (0) 20 3000 5555': '+44 20 3000 5555',
            '+44(0)203 000 5555': '+44 20 3000 5555',
            '00 (44) 2030 005 555': '+44 20 3000 5555',
            '(+44 203) 000 5555': '+44 20 3000 5555',
            '(+44) 203 000 5555': '+44 20 3000 5555',
            '011 44 203 000 5555': '+44 20 3000 5555',
            '020-3000-5555': '+44 20 3000 5555',
            '(020)-3000-5555': '+44 20 3000 5555',
            '+44-20-3000-5555': '+44 20 3000 5555',
            '0203-000-5555': '+44 20 3000 5555',
            '(0203)-000-5555': '+44 20 3000 5555',
            '02030-005-555': '+44 20 3000 5555',
            '+44-(0)-20-3000-5555': '+44 20 3000 5555',
            '+44(0)203-000-5555': '+44 20 3000 5555',
            '00-(44)-2030-005-555': '+44 20 3000 5555',
            '(+44-203)-000-5555': '+44 20 3000 5555',
            '(+44)-203-000-5555': '+44 20 3000 5555',
            '011-44-203-000-5555': '+44 20 3000 5555',
            '0114 223 4567': '+44 114 223 4567',
            '01142 345 567': '+44 114 234 5567',
            '01415 345 567': '+44 141 534 5567',
            '+44 1213 456 789': '+44 121 345 6789',
            '00 44 (0) 1697 73555': '+44 16977 3555',
            '011 44 14 1890 2345': '+44 141 890 2345',
            '011 44 11 4345 2345': '+44 114 345 2345',
            '020 3000 5000': '+44 20 3000 5000',
            '0121 555 7777': '+44 121 555 7777',
            '01750 615777': '+44 1750 615777',
            '019467 55555': '+44 19467 55555',
            '01750 62555': '+44 1750 62555',
            '016977 3555': '+44 16977 3555',
            '0500 777888': '+44 500 777888'
        }
        errors = GBPhoneNumberField.default_error_messages
        messages = {
            'number_format': [errors['number_format'].translate('gb')],
            'number_range': [errors['number_range'].translate('gb')]
        }
        invalid = {
            '011 44 203 000 5555 5': messages['number_format'],
            '+44 20 300 5555': messages['number_format'],
            '025 4555 6777': messages['number_range'],
            '0119 456 4567': messages['number_range'],
            '0623 111 3456': messages['number_range'],
            '0756 334556': messages['number_range'],
            '020 5000 5000': messages['number_range'],
            '0171 555 7777': messages['number_range'],
            '01999 777888': messages['number_range'],
            '01750 61777': messages['number_range']
        }
        self.assertFieldOutput(GBPhoneNumberField, valid, invalid)
