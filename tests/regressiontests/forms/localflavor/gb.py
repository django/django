from django.contrib.localflavor.gb.forms import GBPostcodeField

from django.test import SimpleTestCase


class GBLocalFlavorTests(SimpleTestCase):
    def test_GBPostcodeField(self):
        error_invalid = [u'Enter a valid postcode.']
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
            '1NV 4L1D': [u'Enter a bloody postcode!'],
        }
        kwargs = {'error_messages': {'invalid': 'Enter a bloody postcode!'}}
        self.assertFieldOutput(GBPostcodeField, valid, invalid, field_kwargs=kwargs)
