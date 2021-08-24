from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .. import Error, Tags, Warning, register

CROSS_ORIGIN_OPENER_POLICY_VALUES = {
    "same-origin",
    "same-origin-allow-popups",
    "unsafe-none",
}
REFERRER_POLICY_VALUES = {
    "no-referrer",
    "no-referrer-when-downgrade",
    "origin",
    "origin-when-cross-origin",
    "same-origin",
    "strict-origin",
    "strict-origin-when-cross-origin",
    "unsafe-url",
}

SECRET_KEY_INSECURE_PREFIX = "django-insecure-"
SECRET_KEY_MIN_LENGTH = 50
SECRET_KEY_MIN_UNIQUE_CHARACTERS = 5

W001 = Warning(
    "You do not have 'django.middleware.security.SecurityMiddleware' "
    "in your MIDDLEWARE so the SECURE_HSTS_SECONDS, "
    "SECURE_CONTENT_TYPE_NOSNIFF, SECURE_REFERRER_POLICY, "
    "SECURE_CROSS_ORIGIN_OPENER_POLICY, and SECURE_SSL_REDIRECT settings will "
    "have no effect.",
    id="security.W001",
)

W002 = Warning(
    "You do not have "
    "'django.middleware.clickjacking.XFrameOptionsMiddleware' in your "
    "MIDDLEWARE, so your pages will not be served with an "
    "'x-frame-options' header. Unless there is a good reason for your "
    "site to be served in a frame, you should consider enabling this "
    "header to help prevent clickjacking attacks.",
    id="security.W002",
)

W004 = Warning(
    "You have not set a value for the SECURE_HSTS_SECONDS setting. "
    "If your entire site is served only over SSL, you may want to consider "
    "setting a value and enabling HTTP Strict Transport Security. "
    "Be sure to read the documentation first; enabling HSTS carelessly "
    "can cause serious, irreversible problems.",
    id="security.W004",
)

W005 = Warning(
    "You have not set the SECURE_HSTS_INCLUDE_SUBDOMAINS setting to True. "
    "Without this, your site is potentially vulnerable to attack "
    "via an insecure connection to a subdomain. Only set this to True if "
    "you are certain that all subdomains of your domain should be served "
    "exclusively via SSL.",
    id="security.W005",
)

W006 = Warning(
    "Your SECURE_CONTENT_TYPE_NOSNIFF setting is not set to True, "
    "so your pages will not be served with an "
    "'X-Content-Type-Options: nosniff' header. "
    "You should consider enabling this header to prevent the "
    "browser from identifying content types incorrectly.",
    id="security.W006",
)

W008 = Warning(
    "Your SECURE_SSL_REDIRECT setting is not set to True. "
    "Unless your site should be available over both SSL and non-SSL "
    "connections, you may want to either set this setting True "
    "or configure a load balancer or reverse-proxy server "
    "to redirect all connections to HTTPS.",
    id="security.W008",
)

W009 = Warning(
    "Your SECRET_KEY has less than %(min_length)s characters, less than "
    "%(min_unique_chars)s unique characters, or it's prefixed with "
    "'%(insecure_prefix)s' indicating that it was generated automatically by "
    "Django. Please generate a long and random SECRET_KEY, otherwise many of "
    "Django's security-critical features will be vulnerable to attack."
    % {
        "min_length": SECRET_KEY_MIN_LENGTH,
        "min_unique_chars": SECRET_KEY_MIN_UNIQUE_CHARACTERS,
        "insecure_prefix": SECRET_KEY_INSECURE_PREFIX,
    },
    id="security.W009",
)

W018 = Warning(
    "You should not have DEBUG set to True in deployment.",
    id="security.W018",
)

W019 = Warning(
    "You have "
    "'django.middleware.clickjacking.XFrameOptionsMiddleware' in your "
    "MIDDLEWARE, but X_FRAME_OPTIONS is not set to 'DENY'. "
    "Unless there is a good reason for your site to serve other parts of "
    "itself in a frame, you should change it to 'DENY'.",
    id="security.W019",
)

W020 = Warning(
    "ALLOWED_HOSTS must not be empty in deployment.",
    id="security.W020",
)

W021 = Warning(
    "You have not set the SECURE_HSTS_PRELOAD setting to True. Without this, "
    "your site cannot be submitted to the browser preload list.",
    id="security.W021",
)

W022 = Warning(
    "You have not set the SECURE_REFERRER_POLICY setting. Without this, your "
    "site will not send a Referrer-Policy header. You should consider "
    "enabling this header to protect user privacy.",
    id="security.W022",
)

E023 = Error(
    "You have set the SECURE_REFERRER_POLICY setting to an invalid value.",
    hint="Valid values are: {}.".format(", ".join(sorted(REFERRER_POLICY_VALUES))),
    id="security.E023",
)

E024 = Error(
    "You have set the SECURE_CROSS_ORIGIN_OPENER_POLICY setting to an invalid "
    "value.",
    hint="Valid values are: {}.".format(
        ", ".join(sorted(CROSS_ORIGIN_OPENER_POLICY_VALUES)),
    ),
    id="security.E024",
)


def _security_middleware():
    return "django.middleware.security.SecurityMiddleware" in settings.MIDDLEWARE


def _xframe_middleware():
    return (
        "django.middleware.clickjacking.XFrameOptionsMiddleware" in settings.MIDDLEWARE
    )


@register(Tags.security, deploy=True)
def check_security_middleware(app_configs, **kwargs):
    passed_check = _security_middleware()
    return [] if passed_check else [W001]


@register(Tags.security, deploy=True)
def check_xframe_options_middleware(app_configs, **kwargs):
    passed_check = _xframe_middleware()
    return [] if passed_check else [W002]


@register(Tags.security, deploy=True)
def check_sts(app_configs, **kwargs):
    passed_check = not _security_middleware() or settings.SECURE_HSTS_SECONDS
    return [] if passed_check else [W004]


@register(Tags.security, deploy=True)
def check_sts_include_subdomains(app_configs, **kwargs):
    passed_check = (
        not _security_middleware()
        or not settings.SECURE_HSTS_SECONDS
        or settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    )
    return [] if passed_check else [W005]


@register(Tags.security, deploy=True)
def check_sts_preload(app_configs, **kwargs):
    passed_check = (
        not _security_middleware()
        or not settings.SECURE_HSTS_SECONDS
        or settings.SECURE_HSTS_PRELOAD is True
    )
    return [] if passed_check else [W021]


@register(Tags.security, deploy=True)
def check_content_type_nosniff(app_configs, **kwargs):
    passed_check = (
        not _security_middleware() or settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    )
    return [] if passed_check else [W006]


@register(Tags.security, deploy=True)
def check_ssl_redirect(app_configs, **kwargs):
    passed_check = not _security_middleware() or settings.SECURE_SSL_REDIRECT is True
    return [] if passed_check else [W008]


@register(Tags.security, deploy=True)
def check_secret_key(app_configs, **kwargs):
    try:
        secret_key = settings.SECRET_KEY
    except (ImproperlyConfigured, AttributeError):
        passed_check = False
    else:
        passed_check = (
            len(set(secret_key)) >= SECRET_KEY_MIN_UNIQUE_CHARACTERS
            and len(secret_key) >= SECRET_KEY_MIN_LENGTH
            and not secret_key.startswith(SECRET_KEY_INSECURE_PREFIX)
        )
    return [] if passed_check else [W009]


@register(Tags.security, deploy=True)
def check_debug(app_configs, **kwargs):
    passed_check = not settings.DEBUG
    return [] if passed_check else [W018]


@register(Tags.security, deploy=True)
def check_xframe_deny(app_configs, **kwargs):
    passed_check = not _xframe_middleware() or settings.X_FRAME_OPTIONS == "DENY"
    return [] if passed_check else [W019]


@register(Tags.security, deploy=True)
def check_allowed_hosts(app_configs, **kwargs):
    return [] if settings.ALLOWED_HOSTS else [W020]


@register(Tags.security, deploy=True)
def check_referrer_policy(app_configs, **kwargs):
    if _security_middleware():
        if settings.SECURE_REFERRER_POLICY is None:
            return [W022]
        # Support a comma-separated string or iterable of values to allow fallback.
        if isinstance(settings.SECURE_REFERRER_POLICY, str):
            values = {v.strip() for v in settings.SECURE_REFERRER_POLICY.split(",")}
        else:
            values = set(settings.SECURE_REFERRER_POLICY)
        if not values <= REFERRER_POLICY_VALUES:
            return [E023]
    return []


@register(Tags.security, deploy=True)
def check_cross_origin_opener_policy(app_configs, **kwargs):
    if (
        _security_middleware()
        and settings.SECURE_CROSS_ORIGIN_OPENER_POLICY is not None
        and settings.SECURE_CROSS_ORIGIN_OPENER_POLICY
        not in CROSS_ORIGIN_OPENER_POLICY_VALUES
    ):
        return [E024]
    return []
