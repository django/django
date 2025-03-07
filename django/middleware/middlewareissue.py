from django.template.exceptions import TemplateSyntaxError


class ExampleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        view_context = getattr(request, "view_context", None)
        try:
            response = self.get_response(request)
            print("This should work")
            return response
        except TemplateSyntaxError as error:
            if "Could not parse the remainder" in str(error):
                view_context = getattr(request, "view_context", None)
                print(f"Context from view: {view_context}")
