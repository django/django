from django.contrib.localflavor.pt.forms import PTZipCodeField, PTPhoneNumberField

from utils import LocalFlavorTestCase


class PTLocalFlavorTests(LocalFlavorTestCase):
    def test_PTZipCodeField(self):
        error_format = [u'Enter a zip code in the format XXXX-XXX.']
        valid = {
            '3030-034': '3030-034',
            '1003456': '1003-456',
        }
        invalid = {
            '2A200': error_format,
            '980001': error_format,
        }
        self.assertFieldOutput(PTZipCodeField, valid, invalid)

    def test_PTPhoneNumberField(self):
        error_format = [u'Phone numbers must have 9 digits, or start by + or 00']
        valid = {
            '917845189': '917845189',
            '91 784 5189': '917845189',
            '91 784 5189': '917845189',
            '+351 91 111': '+35191111',
            '00351873': '00351873',
        }
        invalid = {
            '91 784 51 8': error_format,
            '091 456 987 1': error_format,
        }
        self.assertFieldOutput(PTPhoneNumberField, valid, invalid)
