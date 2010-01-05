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

from django.core.exceptions import ValidationError
from widgets import *
from fields import *
from forms import *
from models import *
