from pathlib import Path

from django.conf import settings
from django.http import HttpResponseForbidden
from django.template import Context, Engine, TemplateDoesNotExist, loader
from django.utils.translation import gettext as _
from django.utils.version import get_docs_version

CSRF_FAILURE_TEMPLATE_NAME = "403_csrf.html"


def builtin_template_path(name):
    """
    Return a path to a builtin template.

    Avoid calling this function at the module level or in a class-definition
    because __file__ may not exist, e.g. in frozen environments.
    """
    return Path(__file__).parent / "templates" / name


def csrf_failure(request, reason="", template_name=CSRF_FAILURE_TEMPLATE_NAME):
    """
    Default view used when request fails CSRF protection
    """
    from django.middleware.csrf import REASON_NO_CSRF_COOKIE, REASON_NO_REFERER

    c = {
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
        "no_referer2": _(
            "If you have configured your browser to disable “Referer” headers, "
            "please re-enable them, at least for this site, or for HTTPS "
            "connections, or for “same-origin” requests."
        ),
        "no_referer3": _(
            'If you are using the <meta name="referrer" '
            'content="no-referrer"> tag or including the “Referrer-Policy: '
            "no-referrer” header, please remove them. The CSRF protection "
            "requires the “Referer” header to do strict referer checking. If "
            "you’re concerned about privacy, use alternatives like "
            '<a rel="noreferrer" …> for links to third-party sites.'
        ),
        "no_cookie": reason == REASON_NO_CSRF_COOKIE,
        "no_cookie1": _(
            "You are seeing this message because this site requires a CSRF "
            "cookie when submitting forms. This cookie is required for "
            "security reasons, to ensure that your browser is not being "
            "hijacked by third parties."
        ),
        "no_cookie2": _(
            "If you have configured your browser to disable cookies, please "
            "re-enable them, at least for this site, or for “same-origin” "
            "requests."
        ),
        "DEBUG": settings.DEBUG,
        "docs_version": get_docs_version(),
        "more": _("More information is available with DEBUG=True."),
    }
    try:
        t = loader.get_template(template_name)
        body = t.render(request=request)
    except TemplateDoesNotExist:
        if template_name == CSRF_FAILURE_TEMPLATE_NAME:
            # If the default template doesn't exist, use the fallback template.
            with builtin_template_path("csrf_403.html").open(encoding="utf-8") as fh:
                t = Engine().from_string(fh.read())
            body = t.render(Context(c))
        else:
            # Raise if a developer-specified template doesn't exist.
            raise
    return HttpResponseForbidden(body)
