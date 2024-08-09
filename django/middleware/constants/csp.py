HEADER = "Content-Security-Policy"
HEADER_REPORT_ONLY = "Content-Security-Policy-Report-Only"

NONE = "'none'"
REPORT_SAMPLE = "'report-sample'"
SELF = "'self'"
STRICT_DYNAMIC = "'strict-dynamic'"
UNSAFE_ALLOW_REDIRECTS = "'unsafe-allow-redirects'"
UNSAFE_EVAL = "'unsafe-eval'"
UNSAFE_HASHES = "'unsafe-hashes'"
UNSAFE_INLINE = "'unsafe-inline'"
WASM_UNSAFE_EVAL = "'wasm-unsafe-eval'"


class Nonce:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "django.middleware.constants.csp.NONCE"


NONCE = Nonce()
