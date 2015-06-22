import warnings

from django.forms.widgets import SelectDateWidget
from django.utils.deprecation import RemovedInDjango30Warning

__all__ = ['SelectDateWidget']


warnings.warn(
    "django.forms.extras is deprecated. You can find "
    "SelectDateWidget in django.forms.widgets instead.",
    RemovedInDjango30Warning, stacklevel=2)
