from django.middleware.csrf import CsrfMiddleware, CsrfViewMiddleware, CsrfResponseMiddleware
from django.views.decorators.csrf import csrf_exempt, csrf_view_exempt, csrf_response_exempt

import warnings
warnings.warn("This import for CSRF functionality is deprecated.  Please use django.middleware.csrf for the middleware and django.views.decorators.csrf for decorators.",
              DeprecationWarning
              )
