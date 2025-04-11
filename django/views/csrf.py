from pathlib import Path
from django.conf import settings
from django.template import loader
from django.http import HttpResponseForbidden
from django.utils.translation import gettext as _
from django.utils.version import get_docs_version
from django.template.backends.django import DjangoTemplates


CSRF_FAILURE_TEMPLATE_NAME = "403_csrf.html"


def builtin_template_path(name: str) -> Path:
    """Return path to a builtin template, avoiding \
module-level file access."""
    return Path(__file__).parent / "templates" / name


def csrf_failure(request, reason="",
                 template_name=CSRF_FAILURE_TEMPLATE_NAME):
    """
    Default view for CSRF verification failures with improved template handling.
    """
    from django.middleware.csrf import (REASON_NO_REFERER,
                                        REASON_NO_CSRF_COOKIE)

    context = {
        "title": _("Forbidden"),
        "main": _("CSRF verification failed. Request aborted."),
        "reason": reason,
        "no_referer": reason == REASON_NO_REFERER,
        "no_referer1": _(
            "You are seeing this message because this HTTPS site requires a "
            "“Referer header” to be sent by your web browser, but none was "
            "sent. This header is required for security reasons, to ensure "
            "that your browser is not being hijacked by third parties."
        ),
        # ... (keep other context translations the same as original)
        "DEBUG": settings.DEBUG,
        "docs_version": get_docs_version(),
        "more": _("More information is available with DEBUG=True."),
    }

    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        if template_name == CSRF_FAILURE_TEMPLATE_NAME:
            # Use Django's template system instead of manual file reading
            template = loader.get_template("csrf_403.html")
        else:
            raise

    return HttpResponseForbidden(
        template.render(request=request, context=context))