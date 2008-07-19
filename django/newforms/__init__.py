import warnings
warnings.warn(
    category = DeprecationWarning,
    message = "django.newforms is no longer new. Import django.forms instead.",
    stacklevel = 2
)
from django.forms import *