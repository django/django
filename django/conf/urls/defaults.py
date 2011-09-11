import warnings
warnings.warn("django.conf.urls.defaults is deprecated; use django.conf.urls instead",
              PendingDeprecationWarning)

from django.conf.urls import (handler403, handler404, handler500,
        include, patterns, url)
