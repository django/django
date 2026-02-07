from urllib.parse import quote

from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseServerError,
)
from django.template import Context, Engine, TemplateDoesNotExist, loader
from django.utils.decorators import method_decorator
from django.views.debug import DEBUG_ENGINE
from django.views.decorators.csrf import requires_csrf_token
from django.views.generic.base import ContextMixin, View

ERROR_404_TEMPLATE_NAME = "404.html"
ERROR_403_TEMPLATE_NAME = "403.html"
ERROR_400_TEMPLATE_NAME = "400.html"
ERROR_500_TEMPLATE_NAME = "500.html"
ERROR_PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <title>%(title)s</title>
</head>
<body>
  <h1>%(title)s</h1><p>%(details)s</p>
</body>
</html>
"""


# These views can be called when CsrfViewMiddleware.process_view() not run,
# therefore need @requires_csrf_token in case the template needs
# {% csrf_token %}.


@requires_csrf_token
def page_not_found(request, exception, template_name=ERROR_404_TEMPLATE_NAME):
    """
    Default 404 handler.

    Templates: :template:`404.html`
    Context:
        request_path
            The path of the requested URL (e.g., '/app/pages/bad_page/'). It's
            quoted to prevent a content injection attack.
        exception
            The message from the exception which triggered the 404 (if one was
            supplied), or the exception class name
    """
    exception_repr = exception.__class__.__name__
    # Try to get an "interesting" exception message, if any (and not the ugly
    # Resolver404 dictionary)
    try:
        message = exception.args[0]
    except (AttributeError, IndexError):
        pass
    else:
        if isinstance(message, str):
            exception_repr = message
    context = {
        "request_path": quote(request.path),
        "exception": exception_repr,
    }
    try:
        template = loader.get_template(template_name)
        body = template.render(context, request)
    except TemplateDoesNotExist:
        if template_name != ERROR_404_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        # Render template (even though there are no substitutions) to allow
        # inspecting the context in tests.
        template = Engine().from_string(
            ERROR_PAGE_TEMPLATE
            % {
                "title": "Not Found",
                "details": "The requested resource was not found on this server.",
            },
        )
        body = template.render(Context(context))
    return HttpResponseNotFound(body)


@requires_csrf_token
def server_error(request, template_name=ERROR_500_TEMPLATE_NAME):
    """
    500 error handler.

    Templates: :template:`500.html`
    Context: None
    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        if template_name != ERROR_500_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        return HttpResponseServerError(
            ERROR_PAGE_TEMPLATE % {"title": "Server Error (500)", "details": ""},
        )
    return HttpResponseServerError(template.render())


@requires_csrf_token
def bad_request(request, exception, template_name=ERROR_400_TEMPLATE_NAME):
    """
    400 error handler.

    Templates: :template:`400.html`
    Context: None
    """
    try:
        template = loader.get_template(template_name)
        body = template.render(request=request)
    except TemplateDoesNotExist:
        if template_name != ERROR_400_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        return HttpResponseBadRequest(
            ERROR_PAGE_TEMPLATE % {"title": "Bad Request (400)", "details": ""},
        )
    # No exception content is passed to the template, to not disclose any
    # sensitive information.
    return HttpResponseBadRequest(body)


@requires_csrf_token
def permission_denied(request, exception, template_name=ERROR_403_TEMPLATE_NAME):
    """
    Permission denied (403) handler.

    Templates: :template:`403.html`
    Context:
        exception
            The message from the exception which triggered the 403 (if one was
            supplied).

    If the template does not exist, an Http403 response containing the text
    "403 Forbidden" (as per RFC 9110 Section 15.5.4) will be returned.
    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        if template_name != ERROR_403_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        return HttpResponseForbidden(
            ERROR_PAGE_TEMPLATE % {"title": "403 Forbidden", "details": ""},
        )
    return HttpResponseForbidden(
        template.render(request=request, context={"exception": str(exception)})
    )


@method_decorator(requires_csrf_token, name="dispatch")
class DefaultErrorView(ContextMixin, View):
    status_code = None
    context_by_status = {
        400: {"title": "Bad Request (400)", "details": ""},
        403: {"title": "403 Forbidden", "details": ""},
        404: {
            "title": "Not Found",
            "details": "The requested resource was not found on this server.",
        },
        500: {"title": "Server Error (500)", "details": ""},
    }

    def setup(self, request, exception=None, **kwargs):
        self.exception = exception
        return super().setup(request, **kwargs)

    def get(self, request, *args, **kwargs):
        response_class = HttpResponse.response_class_by_status_code(self.status_code)
        context = self.get_context_data(**kwargs)
        try:
            template = loader.get_template(self.get_template_name())
            content = template.render(context, request)
        except TemplateDoesNotExist:
            template = DEBUG_ENGINE.from_string(ERROR_PAGE_TEMPLATE % context)
            content = template.render(context=Context(context))
        return response_class(content, status=self.status_code)

    def post(self, *args, **kwargs):
        return self.get(*args, **kwargs)

    def get_template_name(self):
        return f"{self.status_code}.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context |= self.context_by_status.get(
            self.status_code, {"title": f"Error ({self.status_code})", "details": ""}
        )
        context |= {
            "request_path": quote(self.request.path),
            "exception": self.exception_as_string(),
        }
        return context

    def exception_as_string(self):
        if self.status_code == 404:
            # Try to get an "interesting" exception message, if any (and not the
            # ugly Resolver404 dictionary)
            try:
                message = self.exception.args[0]
            except (AttributeError, IndexError):
                pass
            else:
                if isinstance(message, str):
                    return message
            return self.exception.__class__.__name__
        return str(self.exception)
