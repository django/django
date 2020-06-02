from urllib.parse import quote

from django.http import (
    HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    HttpResponseServerError,
)
from django.template import Context, Engine, TemplateDoesNotExist, loader
from django.views.decorators.csrf import requires_csrf_token

ERROR_404_TEMPLATE_NAME = '404.html'
ERROR_403_TEMPLATE_NAME = '403.html'
ERROR_400_TEMPLATE_NAME = '400.html'
ERROR_500_TEMPLATE_NAME = '500.html'
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


# This can be called when CsrfViewMiddleware.process_view has not run,
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
        'request_path': quote(request.path),
        'exception': exception_repr,
    }
    try:
        template = loader.get_template(template_name)
        body = template.render(context, request)
        content_type = None             # Django will use 'text/html'.
    except TemplateDoesNotExist:
        if template_name != ERROR_404_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        # Render template (even though there are no substitutions) to allow
        # inspecting the context in tests.
        template = Engine().from_string(
            ERROR_PAGE_TEMPLATE % {
                'title': 'Not Found',
                'details': 'The requested resource was not found on this server.',
            },
        )
        body = template.render(Context(context))
        content_type = 'text/html'
    return HttpResponseNotFound(body, content_type=content_type)


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
            ERROR_PAGE_TEMPLATE % {'title': 'Server Error (500)', 'details': ''},
            content_type='text/html',
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
    except TemplateDoesNotExist:
        if template_name != ERROR_400_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        return HttpResponseBadRequest(
            ERROR_PAGE_TEMPLATE % {'title': 'Bad Request (400)', 'details': ''},
            content_type='text/html',
        )
    # No exception content is passed to the template, to not disclose any sensitive information.
    return HttpResponseBadRequest(template.render())


# This can be called when CsrfViewMiddleware.process_view has not run,
# therefore need @requires_csrf_token in case the template needs
# {% csrf_token %}.
@requires_csrf_token
def permission_denied(request, exception, template_name=ERROR_403_TEMPLATE_NAME):
    """
    Permission denied (403) handler.

    Templates: :template:`403.html`
    Context: None

    If the template does not exist, an Http403 response containing the text
    "403 Forbidden" (as per RFC 7231) will be returned.
    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        if template_name != ERROR_403_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        return HttpResponseForbidden(
            ERROR_PAGE_TEMPLATE % {'title': '403 Forbidden', 'details': ''},
            content_type='text/html',
        )
    return HttpResponseForbidden(
        template.render(request=request, context={'exception': str(exception)})
    )
