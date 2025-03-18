NONE = "'none'"
REPORT_SAMPLE = "'report-sample'"
SELF = "'self'"
STRICT_DYNAMIC = "'strict-dynamic'"
UNSAFE_ALLOW_REDIRECTS = "'unsafe-allow-redirects'"
UNSAFE_EVAL = "'unsafe-eval'"
UNSAFE_HASHES = "'unsafe-hashes'"
UNSAFE_INLINE = "'unsafe-inline'"
WASM_UNSAFE_EVAL = "'wasm-unsafe-eval'"

# NOTE:
# - `NONCE` is a sentinel value used as a placeholder to indicate where the
#   generated nonce should be inserted in the CSP header.
# - The CSP middleware detects this value and replaces it with a unique nonce
#   generated per request.
# - The value itself is arbitrary and should not be mistaken for a real nonce.
NONCE = "<CSP_NONCE_SENTINEL>"
