"""
Decorator for views that supports conditional get on ETag and Last-Modified
headers.
"""

from django.utils.decorators import decorator_from_middleware
from django.middleware.http import ConditionalGetMiddleware

conditional_page = decorator_from_middleware(ConditionalGetMiddleware)
