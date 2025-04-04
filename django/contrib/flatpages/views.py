from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.shortcuts import get_current_site
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404
from django.template import loader
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_protect
from django.utils.module_loading import import_string
from django.core.exceptions import ImproperlyConfigured

DEFAULT_TEMPLATE = "flatpages/default.html"

# This view is called from FlatpageFallbackMiddleware.process_response
# when a 404 is raised, which often means CsrfViewMiddleware.process_view
# has not been called even if CsrfViewMiddleware is installed. So we need
# to use @csrf_protect, in case the template needs {% csrf_token %}.
# However, we can't just wrap this view; if no matching flatpage exists,
# or a redirect is required for authentication, the 404 needs to be returned
# without any CSRF checks. Therefore, we only
# CSRF protect the internal implementation.


def get_context(request, flatpage):
    """
    Dynamically retrieves additional context data for flatpage templates.

    Provides a flexible way to add dynamic context data to flatpage templates.

    It works by:

    1. Reading the FLATPAGE_CONTEXT_GETTER setting, which should be a string path
       to a callable that generates context data
    2. Dynamically importing and calling that function with the current request
       and flatpage objects
    3. Returning the resulting context dictionary to be merged with the base context
       in the render_flatpage function

    Parameters:
        request (HttpRequest): The current HTTP request object
        flatpage (FlatPage): The flatpage object being rendered

    Returns:
        dict: A dictionary of context data to be included in the template rendering
              Returns an empty dict if no context getter is specified

    Raises:
        ImproperlyConfigured: If the specified getter function can't be imported
    """

    # Get the custom context getter function path from Django settings
    getter_string: str | None = getattr(settings, "FLATPAGE_CONTEXT_GETTER", None)

    # No context if no getter specified
    if getter_string is None:
        return {}

    try:
        # Import and instantiate the context getter function dynamically
        # This follows Django's pattern of configurable behavior through settings
        getter = import_string(getter_string)
        return getter(request, flatpage)
    except ImportError:
        # Handle configuration errors where the specified getter function can't be
        # imported
        error_msg = f"Invalid flatpage context getter: {getter_string}"
        raise ImproperlyConfigured(error_msg)


def flatpage(request, url):
    """
    Public interface to the flat page view.

    Models: `flatpages.flatpages`
    Templates: Uses the template defined by the ``template_name`` field,
        or :template:`flatpages/default.html` if template_name is not defined.
    Context:
        flatpage
            `flatpages.flatpages` object
    """
    if not url.startswith("/"):
        url = "/" + url
    site_id = get_current_site(request).id
    try:
        f = get_object_or_404(FlatPage, url=url, sites=site_id)
    except Http404:
        if not url.endswith("/") and settings.APPEND_SLASH:
            url += "/"
            f = get_object_or_404(FlatPage, url=url, sites=site_id)
            return HttpResponsePermanentRedirect("%s/" % request.path)
        else:
            raise
    return render_flatpage(request, f)


@csrf_protect
def render_flatpage(request, f):
    """
    Internal interface to the flat page view.
    """
    # If registration is required for accessing this page, and the user isn't
    # logged in, redirect to the login page.
    if f.registration_required and not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login

        return redirect_to_login(request.path)

    # Template resolution follows a priority order:
    template_names: list[str | None] = [
        # 1. FlatPage.template_name: Template specified in the FlatPage model database entry
        f.template_name,
        # 2. settings.FLATPAGE_DEFAULT_TEMPLATE: Site-wide default from settings
        getattr(settings, "FLATPAGE_DEFAULT_TEMPLATE", None),
        # 3. DEFAULT_TEMPLATE: Hardcoded fallback template name
        DEFAULT_TEMPLATE,
    ]
    # Pass non-empty template names to a template selector
    template = loader.select_template(list(filter(None, template_names)))

    # To avoid having to always use the "|safe" filter in flatpage templates,
    # mark the title and content as already safe (since they are raw HTML
    # content in the first place).
    f.title = mark_safe(f.title)
    f.content = mark_safe(f.content)

    # Create the context dictionary for template rendering
    context = {
        "flatpage": f,  # The FlatPage instance containing the page content
        # Merge in any additional context from the custom context getter
        # This allows for dynamic context data based on the request and flatpage
        **get_context(request, f),
    }

    return HttpResponse(template.render(context, request))
