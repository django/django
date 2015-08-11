import warnings

from django.forms.widgets import SelectDateWidget
from django.utils.deprecation import RemovedInDjango20Warning

__all__ = ['SelectDateWidget']


warnings.warn(
    "django.forms.extras is deprecated. You can find "
    "SelectDateWidget in django.forms.widgets instead.",
    RemovedInDjango20Warning, stacklevel=2)
