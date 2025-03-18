from enum import Enum


class CSP(str, Enum):
    """
    Content Security Policy constants for directive values and special tokens.

    These constants represent:
    1. Standard quoted string values from the CSP spec (e.g., 'self', 'unsafe-inline')
    2. Special placeholder tokens (NONCE) that get replaced by the middleware

    Using this enum instead of raw strings provides better type checking,
    autocompletion, and protection against common mistakes like:

    - Typos (e.g., 'noone' instead of 'none')
    - Missing quotes (e.g., ["self"] instead of ["'self'"])
    - Inconsistent quote styles (e.g., ["'self'", "\"unsafe-inline\""])

    Example usage in Django settings:

        SECURE_CSP = {
            "DIRECTIVES": {
                "default-src": [CSP.NONE],
                "script-src": [CSP.SELF, CSP.NONCE],
            }
        }

    """

    # Standard CSP directive values
    NONE = "'none'"
    REPORT_SAMPLE = "'report-sample'"
    SELF = "'self'"
    STRICT_DYNAMIC = "'strict-dynamic'"
    UNSAFE_ALLOW_REDIRECTS = "'unsafe-allow-redirects'"
    UNSAFE_EVAL = "'unsafe-eval'"
    UNSAFE_HASHES = "'unsafe-hashes'"
    UNSAFE_INLINE = "'unsafe-inline'"
    WASM_UNSAFE_EVAL = "'wasm-unsafe-eval'"

    # Special placeholder that gets replaced by the middleware.
    # The value itself is arbitrary and should not be mistaken for a real nonce.
    NONCE = "<CSP_NONCE_SENTINEL>"
