"Decorator for views that gzips pages if the client supports it."

from django.utils.decorators import decorator_from_middleware
from django.middleware.gzip import GZipMiddleware

gzip_page = decorator_from_middleware(GZipMiddleware)
