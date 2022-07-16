from django.middleware.gzip import GZipMiddleware
from django.utils.decorators import decorator_from_middleware, sync_and_async_middleware

gzip_page = decorator_from_middleware(GZipMiddleware)
gzip_page.__doc__ = "Decorator for views that gzips pages if the client supports it."
gzip_page = sync_and_async_middleware(gzip_page)
