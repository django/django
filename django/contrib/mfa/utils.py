import base64
from importlib import import_module
from io import BytesIO
from urllib.parse import quote

from django.conf import settings


def format_uri(
    *,
    account_name,
    secret_key,
    issuer,
    period=30,
    algorithm="SHA1",
    digits=settings.MFA_DIGITS,
):

    issuer = quote(issuer)
    label = f"{issuer}:{quote(account_name)}" if account_name else issuer

    parameters = (
        f"secret={secret_key}&issuer={issuer}"
        + f"&algorithm={algorithm}&digits={digits}&period={period}"
    )

    return f"otpauth://totp/{label}?{parameters}"


def get_qr_code_module(path):
    try:
        qr_module = import_module(path)
        return qr_module
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            "Specify a path to a QR code generator module in the settings module."
        )


def qr_code_to_bytes(qr_code):
    store = BytesIO()
    qr_code.save(store, format="PNG")
    qr_code_bytes = store.getvalue()
    store.close()
    return qr_code_bytes


def create_b64_qrcode(uri):
    qr_module_path = settings.MFA_QR_MODULE_PATH
    qr_module = get_qr_code_module(qr_module_path)
    qr_code = qr_module.make(uri)
    b64_qr = qr_code_to_bytes(qr_code)
    return base64.b64encode(b64_qr).decode()
