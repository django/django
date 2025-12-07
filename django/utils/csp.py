import secrets
from enum import StrEnum

from django.utils.functional import SimpleLazyObject, empty


class CSP(StrEnum):
    """
    Content Security Policy constants for directive values and special tokens.

    These constants represent:
    1. Standard quoted string values from the CSP spec (e.g., 'self',
       'unsafe-inline')
    2. Special placeholder tokens (NONCE) that get replaced by the middleware

    Using this enum instead of raw strings provides better type checking,
    autocompletion, and protection against common mistakes like:

    - Typos (e.g., 'noone' instead of 'none')
    - Missing quotes (e.g., ["self"] instead of ["'self'"])
    - Inconsistent quote styles (e.g., ["'self'", "\"unsafe-inline\""])

    Example usage in Django settings:

        SECURE_CSP = {
            "default-src": [CSP.NONE],
            "script-src": [CSP.SELF, CSP.NONCE],
        }

    """

    # HTTP Headers.
    HEADER_ENFORCE = "Content-Security-Policy"
    HEADER_REPORT_ONLY = "Content-Security-Policy-Report-Only"

    # Standard CSP directive values.
    NONE = "'none'"
    REPORT_SAMPLE = "'report-sample'"
    SELF = "'self'"
    STRICT_DYNAMIC = "'strict-dynamic'"
    UNSAFE_EVAL = "'unsafe-eval'"
    UNSAFE_HASHES = "'unsafe-hashes'"
    UNSAFE_INLINE = "'unsafe-inline'"
    WASM_UNSAFE_EVAL = "'wasm-unsafe-eval'"

    # Special placeholder that gets replaced by the middleware.
    # The value itself is arbitrary and should not be mistaken for a real
    # nonce.
    NONCE = "<CSP_NONCE_SENTINEL>"


class LazyNonce(SimpleLazyObject):
    """
    Lazily generates a cryptographically secure nonce string, for use in CSP
    headers.

    The nonce is only generated when first accessed (e.g., via string
    interpolation or inside a template).

    The nonce will evaluate as `True` if it has been generated, and `False` if
    it has not. This is useful for third-party Django libraries that want to
    support CSP without requiring it.

    Example Django template usage with context processors enabled:

        <script{% if csp_nonce %} nonce="{{ csp_nonce }}"...{% endif %}>

    The `{% if %}` block will only render if the nonce has been evaluated
    elsewhere.

    """

    def __init__(self):
        super().__init__(self._generate)

    def _generate(self):
        return secrets.token_urlsafe(16)

    def __bool__(self):
        return self._wrapped is not empty


def build_policy(config, nonce=None):
    policy = []

    for directive, values in config.items():
        if values in (None, False):
            continue

        if values is True:
            rendered_value = ""
        else:
            if isinstance(values, set):
                # Sort values for consistency, preventing cache invalidation
                # between requests and ensuring reliable browser caching.
                values = sorted(values)
            elif not isinstance(values, list | tuple):
                values = [values]

            # Replace the nonce sentinel with the actual nonce values, if the
            # sentinel is found and a nonce is provided. Otherwise, remove it.
            if (has_sentinel := CSP.NONCE in values) and nonce:
                values = [f"'nonce-{nonce}'" if v == CSP.NONCE else v for v in values]
            elif has_sentinel:
                values = [v for v in values if v != CSP.NONCE]

            if not values:
                continue

            rendered_value = " ".join(values)

        policy.append(f"{directive} {rendered_value}".rstrip())

    return "; ".join(policy)
