from __future__ import absolute_import

import re

from django.test import SimpleTestCase
from django.contrib.localflavor.au.forms import (AUPostCodeField,
    AUPhoneNumberField, AUStateSelect)

from .forms import AustralianPlaceForm


SELECTED_OPTION_PATTERN = r'<option value="%s" selected="selected">'
BLANK_OPTION_PATTERN = r'<option value="">'
INPUT_VALUE_PATTERN = r'<input[^>]*value="%s"[^>]*>'


class AULocalflavorTests(SimpleTestCase):

    def setUp(self):
        self.form = AustralianPlaceForm(
            {'state':'WA',
             'state_required':'QLD',
             'name':'dummy',
             'postcode':'1234',
             'postcode_required':'4321',
             })

    def test_get_display_methods(self):
        """ Ensure get_*_display() methods are added to model instances. """
        place = self.form.save()
        self.assertEqual(place.get_state_display(), 'Western Australia')
        self.assertEqual(place.get_state_required_display(), 'Queensland')

    def test_default_values(self):
        """ Ensure that default values are selected in forms. """
        form = AustralianPlaceForm()
        self.assertTrue(re.search(SELECTED_OPTION_PATTERN % 'NSW',
                                  str(form['state_default'])))
        self.assertTrue(re.search(INPUT_VALUE_PATTERN % '2500',
                                  str(form['postcode_default'])))

    def test_required(self):
        """ Test that required AUStateFields throw appropriate errors. """
        form = AustralianPlaceForm({'state':'NSW', 'name':'Wollongong'})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['state_required'], [u'This field is required.'])
        self.assertEqual(
            form.errors['postcode_required'], [u'This field is required.'])

    def test_field_blank_option(self):
        """ Test that the empty option is there. """
        self.assertTrue(re.search(BLANK_OPTION_PATTERN,
                                  str(self.form['state'])))

    def test_selected_values(self):
        """ Ensure selected states match the initial values provided. """
        self.assertTrue(re.search(SELECTED_OPTION_PATTERN % 'WA',
                                  str(self.form['state'])))
        self.assertTrue(re.search(SELECTED_OPTION_PATTERN % 'QLD',
                                  str(self.form['state_required'])))
        self.assertTrue(re.search(INPUT_VALUE_PATTERN % '1234',
                                  str(self.form['postcode'])))
        self.assertTrue(re.search(INPUT_VALUE_PATTERN % '4321',
                                  str(self.form['postcode_required'])))

    def test_AUStateSelect(self):
        f = AUStateSelect()
        out = u'''<select name="state">
<option value="ACT">Australian Capital Territory</option>
<option value="NSW" selected="selected">New South Wales</option>
<option value="NT">Northern Territory</option>
<option value="QLD">Queensland</option>
<option value="SA">South Australia</option>
<option value="TAS">Tasmania</option>
<option value="VIC">Victoria</option>
<option value="WA">Western Australia</option>
</select>'''
        self.assertHTMLEqual(f.render('state', 'NSW'), out)

    def test_AUPostCodeField(self):
        error_format = [u'Enter a 4 digit postcode.']
        valid = {
            '1234': '1234',
            '2000': '2000',
        }
        invalid = {
            'abcd': error_format,
            '20001': [u'Ensure this value has at most 4 characters (it has 5).'] + error_format,
        }
        self.assertFieldOutput(AUPostCodeField, valid, invalid)

    def test_AUPhoneNumberField(self):
        error_format = [u'Phone numbers must contain 10 digits.']
        valid = {
            '1234567890': '1234567890',
            '0213456789': '0213456789',
            '02 13 45 67 89': '0213456789',
            '(02) 1345 6789': '0213456789',
            '(02) 1345-6789': '0213456789',
            '(02)1345-6789': '0213456789',
            '0408 123 456': '0408123456',
        }
        invalid = {
            '123': error_format,
            '1800DJANGO': error_format,
        }
        self.assertFieldOutput(AUPhoneNumberField, valid, invalid)
