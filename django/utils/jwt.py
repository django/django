import json
from datetime import datetime

from django.conf import settings
from django.core.signing import Signer, b64_decode, b64_encode
from django.utils import timezone
from django.utils.encoding import force_bytes


class ExpiredToken(Exception):
    pass


class JWTFactory:
    """
    Symmetric signed JWT creation and decoding.
    For encryption and other more advanced usages, you can use third-party
    packages like PyJWT.
    """
    header = {
        "alg": "HS256",
        "typ": "JWT",
    }
    salt = None

    def __init__(self, secret=None):
        self.secret = secret or settings.SECRET_KEY
        salt = self.salt or f'{self.__class__.__module__}.{self.__class__.__name__}'
        self.signer = Signer(key=self.secret, salt=salt, sep='.', algorithm='sha256')

    def make_token(self, payload, valid_for=None):
        def encode(mapping):
            return b64_encode(force_bytes(json.dumps(mapping, separators=(",", ":")))).decode()

        if not isinstance(payload, dict):
            raise TypeError("The payload argument must be a dict.")
        if 'iat' not in payload:
            payload['iat'] = int(timezone.now().timestamp())
        if valid_for:
            payload['exp'] = int((datetime.fromtimestamp(payload['iat']) + valid_for).timestamp())

        segments = [encode(self.header), encode(payload)]
        return self.signer.sign('.'.join(segments))

    def decode_token(self, token):
        value = self.signer.unsign(token)
        header, payload = value.split('.')
        decoded = json.loads(b64_decode(force_bytes(payload)).decode())
        if 'exp' in decoded and timezone.now().timestamp() > decoded['exp']:
            raise ExpiredToken("The token has expired.")
        return decoded
