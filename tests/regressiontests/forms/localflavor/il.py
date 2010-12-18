from django.contrib.localflavor.il.forms import (ILPostalCodeField,
    ILIDNumberField)

from utils import LocalFlavorTestCase


class ILLocalFlavorTests(LocalFlavorTestCase):
    def test_ILPostalCodeField(self):
        error_format = [u'Enter a postal code in the format XXXXX']
        valid = {
            '69973': '69973',
            '699 73': '69973',
            '12345': '12345',
        }
        invalid = {
            '84545x': error_format,
            '123456': error_format,
            '1234': error_format,
            '123 4': error_format,
        }
        self.assertFieldOutput(ILPostalCodeField, valid, invalid)

    def test_ILIDNumberField(self):
        error_invalid = [u'Enter a valid ID number.']
        valid = {
            '3933742-3': '39337423',
            '39337423': '39337423',
            '039337423': '039337423',
            '03933742-3': '039337423',
            '0091': '0091',
        }
        invalid = {
            '123456789': error_invalid,
            '12345678-9': error_invalid,
            '012346578': error_invalid,
            '012346578-': error_invalid,
            '0001': error_invalid,
        }
        self.assertFieldOutput(ILIDNumberField, valid, invalid)
