from django.conf import settings

from .. import Tags, Warning, register
from ..utils import patch_middleware_message

SECRET_KEY_MIN_LENGTH = 50
SECRET_KEY_MIN_UNIQUE_CHARACTERS = 5

W001 = Warning(
    "You do not have 'django.middleware.security.SecurityMiddleware' "
    "in your MIDDLEWARE so the SECURE_HSTS_SECONDS, "
    "SECURE_CONTENT_TYPE_NOSNIFF, "
    "SECURE_BROWSER_XSS_FILTER, and SECURE_SSL_REDIRECT settings "
    "will have no effect.",
    id='security.W001',
)

W002 = Warning(
    "You do not have "
    "'django.middleware.clickjacking.XFrameOptionsMiddleware' in your "
    "MIDDLEWARE, so your pages will not be served with an "
    "'x-frame-options' header. Unless there is a good reason for your "
    "site to be served in a frame, you should consider enabling this "
    "header to help prevent clickjacking attacks.",
    id='security.W002',
)

W004 = Warning(
    "You have not set a value for the SECURE_HSTS_SECONDS setting. "
    "If your entire site is served only over SSL, you may want to consider "
    "setting a value and enabling HTTP Strict Transport Security. "
    "Be sure to read the documentation first; enabling HSTS carelessly "
    "can cause serious, irreversible problems.",
    id='security.W004',
)

W005 = Warning(
    "You have not set the SECURE_HSTS_INCLUDE_SUBDOMAINS setting to True. "
    "Without this, your site is potentially vulnerable to attack "
    "via an insecure connection to a subdomain. Only set this to True if "
    "you are certain that all subdomains of your domain should be served "
    "exclusively via SSL.",
    id='security.W005',
)

W006 = Warning(
    "Your SECURE_CONTENT_TYPE_NOSNIFF setting is not set to True, "
    "so your pages will not be served with an "
    "'x-content-type-options: nosniff' header. "
    "You should consider enabling this header to prevent the "
    "browser from identifying content types incorrectly.",
    id='security.W006',
)

W007 = Warning(
    "Your SECURE_BROWSER_XSS_FILTER setting is not set to True, "
    "so your pages will not be served with an "
    "'x-xss-protection: 1; mode=block' header. "
    "You should consider enabling this header to activate the "
    "browser's XSS filtering and help prevent XSS attacks.",
    id='security.W007',
)

W008 = Warning(
    "Your SECURE_SSL_REDIRECT setting is not set to True. "
    "Unless your site should be available over both SSL and non-SSL "
    "connections, you may want to either set this setting True "
    "or configure a load balancer or reverse-proxy server "
    "to redirect all connections to HTTPS.",
    id='security.W008',
)

W009 = Warning(
    "Your SECRET_KEY has less than %(min_length)s characters or less than "
    "%(min_unique_chars)s unique characters. Please generate a long and random "
    "SECRET_KEY, otherwise many of Django's security-critical features will be "
    "vulnerable to attack." % {
        'min_length': SECRET_KEY_MIN_LENGTH,
        'min_unique_chars': SECRET_KEY_MIN_UNIQUE_CHARACTERS,
    },
    id='security.W009',
)

W018 = Warning(
    "You should not have DEBUG set to True in deployment.",
    id='security.W018',
)

W019 = Warning(
    "You have "
    "'django.middleware.clickjacking.XFrameOptionsMiddleware' in your "
    "MIDDLEWARE, but X_FRAME_OPTIONS is not set to 'DENY'. "
    "The default is 'SAMEORIGIN', but unless there is a good reason for "
    "your site to serve other parts of itself in a frame, you should "
    "change it to 'DENY'.",
    id='security.W019',
)

W020 = Warning(
    "ALLOWED_HOSTS must not be empty in deployment.",
    id='security.W020',
)


def _security_middleware():
    return ("django.middleware.security.SecurityMiddleware" in settings.MIDDLEWARE_CLASSES or
            settings.MIDDLEWARE and "django.middleware.security.SecurityMiddleware" in settings.MIDDLEWARE)


def _xframe_middleware():
    return ("django.middleware.clickjacking.XFrameOptionsMiddleware" in settings.MIDDLEWARE_CLASSES or
            settings.MIDDLEWARE and "django.middleware.clickjacking.XFrameOptionsMiddleware" in settings.MIDDLEWARE)


@register(Tags.security, deploy=True)
def check_security_middleware(app_configs, **kwargs):
    passed_check = _security_middleware()
    return [] if passed_check else [patch_middleware_message(W001)]


@register(Tags.security, deploy=True)
def check_xframe_options_middleware(app_configs, **kwargs):
    passed_check = _xframe_middleware()
    return [] if passed_check else [patch_middleware_message(W002)]


@register(Tags.security, deploy=True)
def check_sts(app_configs, **kwargs):
    passed_check = not _security_middleware() or settings.SECURE_HSTS_SECONDS
    return [] if passed_check else [W004]


@register(Tags.security, deploy=True)
def check_sts_include_subdomains(app_configs, **kwargs):
    passed_check = (
        not _security_middleware() or
        not settings.SECURE_HSTS_SECONDS or
        settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    )
    return [] if passed_check else [W005]


@register(Tags.security, deploy=True)
def check_content_type_nosniff(app_configs, **kwargs):
    passed_check = (
        not _security_middleware() or
        settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    )
    return [] if passed_check else [W006]


@register(Tags.security, deploy=True)
def check_xss_filter(app_configs, **kwargs):
    passed_check = (
        not _security_middleware() or
        settings.SECURE_BROWSER_XSS_FILTER is True
    )
    return [] if passed_check else [W007]


@register(Tags.security, deploy=True)
def check_ssl_redirect(app_configs, **kwargs):
    passed_check = (
        not _security_middleware() or
        settings.SECURE_SSL_REDIRECT is True
    )
    return [] if passed_check else [W008]


@register(Tags.security, deploy=True)
def check_secret_key(app_configs, **kwargs):
    passed_check = (
        getattr(settings, 'SECRET_KEY', None) and
        len(set(settings.SECRET_KEY)) >= SECRET_KEY_MIN_UNIQUE_CHARACTERS and
        len(settings.SECRET_KEY) >= SECRET_KEY_MIN_LENGTH
    )
    return [] if passed_check else [W009]


@register(Tags.security, deploy=True)
def check_debug(app_configs, **kwargs):
    passed_check = not settings.DEBUG
    return [] if passed_check else [W018]


@register(Tags.security, deploy=True)
def check_xframe_deny(app_configs, **kwargs):
    passed_check = (
        not _xframe_middleware() or
        settings.X_FRAME_OPTIONS == 'DENY'
    )
    return [] if passed_check else [patch_middleware_message(W019)]


@register(Tags.security, deploy=True)
def check_allowed_hosts(app_configs, **kwargs):
    return [] if settings.ALLOWED_HOSTS else [W020]
