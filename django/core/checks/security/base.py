import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .. import Error, Tags, Warning, register

# XXX: Links to related information:
#      - https://www.chromestatus.com/feature/5756689661820928
#      - https://www.chromestatus.com/feature/5744681033924608
DOCUMENT_POLICY_DIRECTIVES = {
    'document-write', 'font-display-late-swap', 'layout-animations',
    'legacy-image-formats', 'oversized-images', 'unoptimized-lossless-images',
    'unoptimized-lossy-images', 'unsized-media',
    # Other:
    'force-load-at-top',
}

# XXX: Links to related information:
#      - https://github.com/w3c/webappsec-permissions-policy/blob/master/features.md
#      - https://developer.mozilla.org/en-US/docs/Web/HTTP/Feature_Policy
#      - https://www.chromestatus.com/feature/5745992911552512
PERMISSIONS_POLICY_DIRECTIVES = {
    # Standardized Features:
    'accelerometer', 'ambient-light-sensor', 'autoplay', 'battery', 'camera',
    'cross-origin-isolated', 'display-capture', 'document-domain',
    'encrypted-media', 'execution-while-not-rendered',
    'execution-while-out-of-viewport', 'fullscreen', 'geolocation',
    'gyroscope', 'magnetometer', 'microphone', 'midi', 'navigation-override',
    'payment', 'picture-in-picture', 'publickey-credentials-get',
    'screen-wake-lock', 'sync-xhr', 'usb', 'web-share', 'xr-spatial-tracking',
    # Proposed Features:
    'clipboard-read', 'clipboard-write', 'gamepad', 'speaker-selection',
    # Experimental Features:
    'conversion-measurement', 'focus-without-user-activation', 'hid',
    'idle-detection', 'serial', 'sync-script', 'trust-token-redemption',
    'vertical-scroll',
    # Other:
    'vibrate',
    # Legacy:
    'lazyload', 'loading-frame-default-eager', 'loading-image-default-eager',
    'vr', 'wake-lock', 'webauthn',
}

REFERRER_POLICY_VALUES = {
    'no-referrer', 'no-referrer-when-downgrade', 'origin',
    'origin-when-cross-origin', 'same-origin', 'strict-origin',
    'strict-origin-when-cross-origin', 'unsafe-url',
}

SECRET_KEY_MIN_LENGTH = 50
SECRET_KEY_MIN_UNIQUE_CHARACTERS = 5

W001 = Warning(
    "You do not have 'django.middleware.security.SecurityMiddleware' "
    "in your MIDDLEWARE so the SECURE_HSTS_SECONDS, "
    "SECURE_CONTENT_TYPE_NOSNIFF, SECURE_BROWSER_XSS_FILTER, "
    "SECURE_PERMISSIONS_POLICY, SECURE_REFERRER_POLICY, and "
    "SECURE_SSL_REDIRECT settings will have no effect.",
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
    "'X-Content-Type-Options: nosniff' header. "
    "You should consider enabling this header to prevent the "
    "browser from identifying content types incorrectly.",
    id='security.W006',
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
    "Unless there is a good reason for your site to serve other parts of "
    "itself in a frame, you should change it to 'DENY'.",
    id='security.W019',
)

W020 = Warning(
    "ALLOWED_HOSTS must not be empty in deployment.",
    id='security.W020',
)

W021 = Warning(
    "You have not set the SECURE_HSTS_PRELOAD setting to True. Without this, "
    "your site cannot be submitted to the browser preload list.",
    id='security.W021',
)

W022 = Warning(
    'You have not set the SECURE_REFERRER_POLICY setting. Without this, your '
    'site will not send a Referrer-Policy header. You should consider '
    'enabling this header to protect user privacy.',
    id='security.W022',
)

E023 = Error(
    'You have set the SECURE_REFERRER_POLICY setting to an invalid value.',
    hint='Valid values are: {}.'.format(', '.join(sorted(REFERRER_POLICY_VALUES))),
    id='security.E023',
)

W024 = Warning(
    'You have not set the SECURE_PERMISSIONS_POLICY setting. Without this, '
    'your site will not send a Permissions-Policy header. You should consider '
    'enabling this header to protect user privacy.',
    id='security.W024',
)

E025 = Error(
    'You have set the SECURE_PERMISSIONS_POLICY setting to an invalid value.',
    hint=(
        'Expected a dictionary with directives as keys and a list of strings '
        'of allowed origins as values. Valid directives are: {}.'
        .format(', '.join(sorted(PERMISSIONS_POLICY_DIRECTIVES)))
    ),
    id='security.E025',
)

E100 = Error(
    "DEFAULT_HASHING_ALGORITHM must be 'sha1' or 'sha256'.",
    id='security.E100',
)


def _security_middleware():
    return 'django.middleware.security.SecurityMiddleware' in settings.MIDDLEWARE


def _xframe_middleware():
    return 'django.middleware.clickjacking.XFrameOptionsMiddleware' in settings.MIDDLEWARE


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
        not _security_middleware() or
        not settings.SECURE_HSTS_SECONDS or
        settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    )
    return [] if passed_check else [W005]


@register(Tags.security, deploy=True)
def check_sts_preload(app_configs, **kwargs):
    passed_check = (
        not _security_middleware() or
        not settings.SECURE_HSTS_SECONDS or
        settings.SECURE_HSTS_PRELOAD is True
    )
    return [] if passed_check else [W021]


@register(Tags.security, deploy=True)
def check_content_type_nosniff(app_configs, **kwargs):
    passed_check = (
        not _security_middleware() or
        settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    )
    return [] if passed_check else [W006]


@register(Tags.security, deploy=True)
def check_ssl_redirect(app_configs, **kwargs):
    passed_check = (
        not _security_middleware() or
        settings.SECURE_SSL_REDIRECT is True
    )
    return [] if passed_check else [W008]


@register(Tags.security, deploy=True)
def check_secret_key(app_configs, **kwargs):
    try:
        secret_key = settings.SECRET_KEY
    except (ImproperlyConfigured, AttributeError):
        passed_check = False
    else:
        passed_check = (
            len(set(secret_key)) >= SECRET_KEY_MIN_UNIQUE_CHARACTERS and
            len(secret_key) >= SECRET_KEY_MIN_LENGTH
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
            values = {v.strip() for v in settings.SECURE_REFERRER_POLICY.split(',')}
        else:
            values = set(settings.SECURE_REFERRER_POLICY)
        if not values <= REFERRER_POLICY_VALUES:
            return [E023]
    return []


@register(Tags.security, deploy=True)
def check_permissions_policy(app_configs, **kwargs):
    if _security_middleware():
        if settings.SECURE_PERMISSIONS_POLICY is None:
            return [W024]
        origin_regex = re.compile(r'^[A-Za-z][-+\.A-Za-z0-9]+://[-\.\w]+(?::\d+)?$', re.ASCII)
        if (
            not isinstance(settings.SECURE_PERMISSIONS_POLICY, dict) or
            not PERMISSIONS_POLICY_DIRECTIVES.issuperset(settings.SECURE_PERMISSIONS_POLICY) or
            not all(
                isinstance(v, (list, tuple)) and all(
                    (isinstance(i, str) and (i in {'*', 'self'} or origin_regex.match(i))) for i in v
                ) for v in settings.SECURE_PERMISSIONS_POLICY.values()
            )
        ):
            return [E025]
    return []


# RemovedInDjango40Warning
@register(Tags.security)
def check_default_hashing_algorithm(app_configs, **kwargs):
    if settings.DEFAULT_HASHING_ALGORITHM not in {'sha1', 'sha256'}:
        return [E100]
    return []
