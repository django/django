from django.conf import settings
from .. import register, Tags, Warning


@register(Tags.security, deploy=True)
def check_security_middleware(app_configs):
    passed_check = "django.middleware.security.SecurityMiddleware" in settings.MIDDLEWARE_CLASSES
    return [] if passed_check else [Warning(
        "You do not have 'django.middleware.security.SecurityMiddleware' "
        "in your MIDDLEWARE_CLASSES so the HSTS_SECONDS, "
        "CONTENT_TYPE_NOSNIFF, "
        "BROWSER_XSS_FILTER and SSL_REDIRECT settings "
        "will have no effect.",
        hint=None,
        id='security.W001',
    )]


@register(Tags.security, deploy=True)
def check_xframe_options_middleware(app_configs):
    passed_check = "django.middleware.clickjacking.XFrameOptionsMiddleware" in settings.MIDDLEWARE_CLASSES
    return [] if passed_check else [Warning(
        "You do not have "
        "'django.middleware.clickjacking.XFrameOptionsMiddleware' in your "
        "MIDDLEWARE_CLASSES, so your pages will not be served with an "
        "'x-frame-options' header. Unless there is a good reason for your "
        "site to be served in a frame, you should consider enabling this "
        "header to help prevent clickjacking attacks.",
        hint=None,
        id='security.W002',
    )]


@register(Tags.security, deploy=True)
def check_sts(app_configs):
    passed_check = bool(settings.SECURITY_MIDDLEWARE['HSTS_SECONDS'])
    return [] if passed_check else [Warning(
        "You have not set a value for the HSTS_SECONDS setting. "
        "If your entire site is served only over SSL, you may want to consider "
        "setting a value and enabling HTTP Strict Transport Security.",
        hint=None,
        id='security.W004',
    )]


@register(Tags.security, deploy=True)
def check_sts_include_subdomains(app_configs):
    passed_check = bool(settings.SECURITY_MIDDLEWARE['HSTS_INCLUDE_SUBDOMAINS'])
    return [] if passed_check else [Warning(
        "You have not set the HSTS_INCLUDE_SUBDOMAINS setting to True. "
        "Without this, your site is potentially vulnerable to attack "
        "via an insecure connection to a subdomain.",
        hint=None,
        id='security.W005',
    )]


def check_content_type_nosniff(app_configs):
    passed_check = settings.SECURITY_MIDDLEWARE['CONTENT_TYPE_NOSNIFF']
    return [] if passed_check else [Warning(
        "Your CONTENT_TYPE_NOSNIFF setting is not set to True, "
        "so your pages will not be served with an "
        "'x-content-type-options: nosniff' header. "
        "You should consider enabling this header to prevent the "
        "browser from identifying content types incorrectly.",
        hint=None,
        id='security.W006',
    )]


@register(Tags.security, deploy=True)
def check_xss_filter(app_configs):
    passed_check = settings.SECURITY_MIDDLEWARE['BROWSER_XSS_FILTER'] is True
    return [] if passed_check else [Warning(
        "Your BROWSER_XSS_FILTER setting is not set to True, "
        "so your pages will not be served with an "
        "'x-xss-protection: 1; mode=block' header. "
        "You should consider enabling this header to activate the "
        "browser's XSS filtering and help prevent XSS attacks.",
        hint=None,
        id='security.W007',
    )]


@register(Tags.security, deploy=True)
def check_ssl_redirect(app_configs):
    passed_check = bool(settings.SECURITY_MIDDLEWARE['SSL_REDIRECT'])
    return [] if passed_check else [Warning(
        "Your SSL_REDIRECT setting is not set to True. "
        "Unless your site should be available over both SSL and non-SSL "
        "connections, you may want to either set this setting to True "
        "or configure a load balancer or reverse-proxy server "
        "to redirect all connections to HTTPS.",
        hint=None,
        id='security.W008',
    )]


@register(Tags.security, deploy=True)
def check_secret_key(app_configs):
    passed_check = (
        getattr(settings, 'SECRET_KEY', None) and
        len(set(settings.SECRET_KEY)) >= 10 and  # at least 10 unique characters
        len(settings.SECRET_KEY) >= 50  # at least 50 characters in length
    )
    return [] if passed_check else [Warning(
        "Your SECRET_KEY has less than 50 characters or less than 10 unique "
        "characters. Please generate a long and random SECRET_KEY, otherwise "
        "many of Django's security-critical features will be vulnerable to "
        "attack.",
        hint=None,
        id='security.W009',
    )]
