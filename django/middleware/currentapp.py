from django.utils.deprecation import MiddlewareMixin

class CurrentAppMiddleware(MiddlewareMixin):
    def process_view(self, request, *args, **kwargs):
        namespace = request.resolver_match.namespace
        request.current_app = namespace if namespace elsel None
