from django.conf import settings
from django.http import HttpResponseForbidden
from django.template import Context, Engine
from django.utils.translation import ugettext as _
from django.utils.version import get_docs_version


# We include the template inline since we need to be able to reliably display
# this error message, especially for the sake of developers, and there isn't any
# other way of making it available independent of what is in the settings file.

# Only the text appearing with DEBUG=False is translated. Normal translation
# tags cannot be used with this inline templates as makemessages would not be
# able to discover the strings.

CSRF_FAILURE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8">
  <meta name="robots" content="NONE,NOARCHIVE">
  <title>403 Forbidden</title>
  <style type="text/css">
    html * { padding:0; margin:0; }
    body * { padding:10px 20px; }
    body * * { padding:0; }
    body { font:small sans-serif; background:#eee; }
    body>div { border-bottom:1px solid #ddd; }
    h1 { font-weight:normal; margin-bottom:.4em; }
    h1 span { font-size:60%; color:#666; font-weight:normal; }
    #info { background:#f6f6f6; }
    #info ul { margin: 0.5em 4em; }
    #info p, #summary p { padding-top:10px; }
    #summary { background: #ffc; }
    #explanation { background:#eee; border-bottom: 0px none; }
  </style>
</head>
<body>
<div id="summary">
  <h1>{{ title }} <span>(403)</span></h1>
  <p>{{ main }}</p>
{% if no_referer %}
  <p>{{ no_referer1 }}</p>
  <p>{{ no_referer2 }}</p>
{% endif %}
{% if no_cookie %}
  <p>{{ no_cookie1 }}</p>
  <p>{{ no_cookie2 }}</p>
{% endif %}
</div>
{% if DEBUG %}
<div id="info">
  <h2>Help</h2>
    {% if reason %}
    <p>Reason given for failure:</p>
    <pre>
    {{ reason }}
    </pre>
    {% endif %}

  <p>In general, this can occur when there is a genuine Cross Site Request Forgery, or when
  <a
  href="https://docs.djangoproject.com/en/{{ docs_version }}/ref/csrf/">Django's
  CSRF mechanism</a> has not been used correctly.  For POST forms, you need to
  ensure:</p>

  <ul>
    <li>Your browser is accepting cookies.</li>

    <li>The view function passes a <code>request</code> to the template's <a
    href="https://docs.djangoproject.com/en/dev/topics/templates/#django.template.backends.base.Template.render"><code>render</code></a>
    method.</li>

    <li>In the template, there is a <code>{% templatetag openblock %} csrf_token
    {% templatetag closeblock %}</code> template tag inside each POST form that
    targets an internal URL.</li>

    <li>If you are not using <code>CsrfViewMiddleware</code>, then you must use
    <code>csrf_protect</code> on any views that use the <code>csrf_token</code>
    template tag, as well as those that accept the POST data.</li>

  </ul>

  <p>You're seeing the help section of this page because you have <code>DEBUG =
  True</code> in your Django settings file. Change that to <code>False</code>,
  and only the initial error message will be displayed.  </p>

  <p>You can customize this page using the CSRF_FAILURE_VIEW setting.</p>
</div>
{% else %}
<div id="explanation">
  <p><small>{{ more }}</small></p>
</div>
{% endif %}
</body>
</html>
"""


def csrf_failure(request, reason=""):
    """
    Default view used when request fails CSRF protection
    """
    from django.middleware.csrf import REASON_NO_REFERER, REASON_NO_CSRF_COOKIE
    t = Engine().from_string(CSRF_FAILURE_TEMPLATE)
    c = Context({
        'title': _("Forbidden"),
        'main': _("CSRF verification failed. Request aborted."),
        'reason': reason,
        'no_referer': reason == REASON_NO_REFERER,
        'no_referer1': _(
            "You are seeing this message because this HTTPS site requires a "
            "'Referer header' to be sent by your Web browser, but none was "
            "sent. This header is required for security reasons, to ensure "
            "that your browser is not being hijacked by third parties."),
        'no_referer2': _(
            "If you have configured your browser to disable 'Referer' headers, "
            "please re-enable them, at least for this site, or for HTTPS "
            "connections, or for 'same-origin' requests."),
        'no_cookie': reason == REASON_NO_CSRF_COOKIE,
        'no_cookie1': _(
            "You are seeing this message because this site requires a CSRF "
            "cookie when submitting forms. This cookie is required for "
            "security reasons, to ensure that your browser is not being "
            "hijacked by third parties."),
        'no_cookie2': _(
            "If you have configured your browser to disable cookies, please "
            "re-enable them, at least for this site, or for 'same-origin' "
            "requests."),
        'DEBUG': settings.DEBUG,
        'docs_version': get_docs_version(),
        'more': _("More information is available with DEBUG=True."),
    })
    return HttpResponseForbidden(t.render(c), content_type='text/html')
