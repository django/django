"""
Django validation and HTML form handling.

TODO:
    Default value for field
    Field labels
    Nestable Forms
    FatalValidationError -- short-circuits all other validators on a form
    ValidationWarning
    "This form field requires foo.js" and form.js_includes()
"""

from __future__ import absolute_import

from django.core.exceptions import ValidationError
from django.forms.fields import *
from django.forms.forms import *
from django.forms.models import *
from django.forms.widgets import *
