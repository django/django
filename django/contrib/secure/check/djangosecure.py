from django.conf import settings

from ..conf import conf
from .util import boolean_check


@boolean_check("SECURITY_MIDDLEWARE_NOT_INSTALLED")
def check_security_middleware():
    return ("django.contrib.secure.middleware.SecurityMiddleware" in
            settings.MIDDLEWARE_CLASSES)

check_security_middleware.messages = {
    "SECURITY_MIDDLEWARE_NOT_INSTALLED": (
        "You do not have 'django.contrib.secure.middleware.SecurityMiddleware' "
        "in your MIDDLEWARE_CLASSES, so the SECURE_HSTS_SECONDS, "
        "SECURE_CONTENT_TYPE_NOSNIFF, "
        "SECURE_BROWSER_XSS_FILTER and SECURE_SSL_REDIRECT settings "
        "will have no effect.")
    }


@boolean_check("STRICT_TRANSPORT_SECURITY_NOT_ENABLED")
def check_sts():
    return bool(conf.SECURE_HSTS_SECONDS)

check_sts.messages = {
    "STRICT_TRANSPORT_SECURITY_NOT_ENABLED": (
        "You have not set a value for the SECURE_HSTS_SECONDS setting. "
        "If your entire site is served only over SSL, you may want to consider "
        "setting a value and enabling HTTP Strict Transport Security "
        "(see http://en.wikipedia.org/wiki/Strict_Transport_Security)."
        )
    }


@boolean_check("STRICT_TRANSPORT_SECURITY_NO_SUBDOMAINS")
def check_sts_include_subdomains():
    return bool(conf.SECURE_HSTS_INCLUDE_SUBDOMAINS)

check_sts_include_subdomains.messages = {
    "STRICT_TRANSPORT_SECURITY_NO_SUBDOMAINS": (
        "You have not set the SECURE_HSTS_INCLUDE_SUBDOMAINS setting to True. "
        "Without this, your site is potentially vulnerable to attack "
        "via an insecure connection to a subdomain."
        )
    }


@boolean_check("CONTENT_TYPE_NOSNIFF_NOT_ENABLED")
def check_content_type_nosniff():
    return conf.SECURE_CONTENT_TYPE_NOSNIFF

check_content_type_nosniff.messages = {
    "CONTENT_TYPE_NOSNIFF_NOT_ENABLED": (
        "Your SECURE_CONTENT_TYPE_NOSNIFF setting is not set to True, "
        "so your pages will not be served with an "
        "'x-content-type-options: nosniff' header. "
        "You should consider enabling this header to prevent the "
        "browser from identifying content types incorrectly."
        )
    }


@boolean_check("BROWSER_XSS_FILTER_NOT_ENABLED")
def check_xss_filter():
    return conf.SECURE_BROWSER_XSS_FILTER

check_xss_filter.messages = {
    "BROWSER_XSS_FILTER_NOT_ENABLED": (
        "Your SECURE_BROWSER_XSS_FILTER setting is not set to True, "
        "so your pages will not be served with an "
        "'x-xss-protection: 1; mode=block' header. "
        "You should consider enabling this header to activate the "
        "browser's XSS filtering and help prevent XSS attacks."
        )
    }


@boolean_check("SSL_REDIRECT_NOT_ENABLED")
def check_ssl_redirect():
    return conf.SECURE_SSL_REDIRECT

check_ssl_redirect.messages = {
    "SSL_REDIRECT_NOT_ENABLED": (
        "Your SECURE_SSL_REDIRECT setting is not set to True. "
        "Unless your site should be available over both SSL and non-SSL "
        "connections, you may want to either set this setting True "
        "or configure a loadbalancer or reverse-proxy server "
        "to redirect all connections to HTTPS."
        )
    }


@boolean_check("BAD_SECRET_KEY")
def check_secret_key():
    if getattr(settings, 'SECRET_KEY', None):
        return len(set(conf.SECRET_KEY)) >= 5
    else:
        return False

check_ssl_redirect.messages = {
    "BAD_SECRET_KEY": (
        "Your SECRET_KEY is either an empty string, non-existent, or has not "
        "enough characters. Please generate a long and random SECRET_KEY, "
        "otherwise many of Django's security-critical features will be "
        "vulnerable to attack."
        )
    }
