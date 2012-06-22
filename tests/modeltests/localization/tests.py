from __future__ import absolute_import

from django.test import TestCase
from django.db import models
from django.utils import translation
from django.utils.formats import (get_format, date_format, time_format,
    localize, localize_input, iter_format_modules, get_format_modules,
    number_format)

'''
Ticket #18471
Add functionality in ModelField to localize their underlying FormFields and Widgets. This will allow to show localized information in the Admin site. Specially usefull for Dates and decimal fields.  
'''
class LocalizationTests(TestCase):
    def test_localization(self):
        #If the field is localize it must localize the underlying formfield and widget. Otherwise it must not localize it.
        localized_field = models.DecimalField(max_digits=5, decimal_places=2, localize = True)
        default_field = models.DecimalField(max_digits=5, decimal_places=2)
        
        self.assertEqual(localized_field.localize, True)
        self.assertEqual(default_field.localize, False)

        self.assertEqual(localized_field.formfield().localize, True)
        self.assertEqual(default_field.formfield().localize, False)
        
        self.assertEqual(localized_field.formfield().widget.is_localized, True)
        self.assertEqual(default_field.formfield().widget.is_localized, False)
        
