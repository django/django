"""Views for handling HTTP requests."""

from django.shortcuts import render  # This import is actually used


def index(request):
    """
    Render the index page with a hello world message.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: The rendered template response.
    """
    message_text = "hello world"
    context = {"message": message_text}
    request.view_context = context
    return render(request, "myfirst.html", context)
