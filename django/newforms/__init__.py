"""
Django validation and HTML form handling.

TODO:
    Validation not tied to a particular field
    Default value for field
    Field labels
    Nestable Forms
    FatalValidationError -- short-circuits all other validators on a form
    ValidationWarning
    "This form field requires foo.js" and form.js_includes()
"""

from widgets import *
from fields import *
from forms import Form

##########################
# DATABASE API SHORTCUTS #
##########################

def form_for_model(model):
    "Returns a Form instance for the given Django model class."
    raise NotImplementedError

def form_for_fields(field_list):
    "Returns a Form instance for the given list of Django database field instances."
    raise NotImplementedError
