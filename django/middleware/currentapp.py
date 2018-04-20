"""
CurrentAppMiddleware

This module provides a middleware that adds current_app attribute to request objects.
"""

from django.utils.deprecation import MiddlewareMixin  # isort:skip

class CurrentAppMiddleware(MiddlewareMixin):
    def process_view(self, request, *args, **kwargs):
        namespace = request.resolver_match.namespace
        request.current_app = namespace if namespace else None
