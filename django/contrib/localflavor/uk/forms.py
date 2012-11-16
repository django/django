from django.contrib.localflavor.gb import forms

import warnings
warnings.warn(
    'The "UK" prefix for United Kingdom has been deprecated in favour of the '
    'GB code. Please use the new GB-prefixed names.', DeprecationWarning, stacklevel=2)

UKPostcodeField = forms.GBPostcodeField
UKCountySelect = forms.GBCountySelect
UKNationSelect = forms.GBNationSelect
