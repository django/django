import base64
import hashlib
import hmac
import math
import secrets
import time
import uuid
from hmac import compare_digest as constant_compare


def create_otp_key(nbytes=20):
    key = secrets.token_hex(nbytes=nbytes)
    return key


def secret_key_b32(key):
    key_byte = key.encode("utf-8")
    key_b32 = base64.b32encode(key_byte)
    return key_b32.decode("utf-8")


class OTP:
    def __init__(self, secret_key, network_delay=1, digits=6):
        self.secret_key = secret_key.encode("utf-8")
        self.network_delay = network_delay
        self.digits = digits

    def verify(self, submitted_otp):
        raise NotImplemented

    def generate(self, *, msg):
        digest = self.hmac_digest(msg=msg)
        offset = self.calculate_offset(digest)
        truncated_code = self.dynamic_binary_code(digest, offset)
        otp = str(truncated_code % 10**self.digits)
        return otp.zfill(self.digits)

    def hmac_digest(self, *, msg, digestmode="sha1"):
        hasher = hmac.new(self.secret_key, msg, digestmode)
        return hasher.digest()

    def calculate_offset(self, digest):
        low_order_byte_index = len(digest) - 1
        offset = digest[low_order_byte_index] & 0xF
        return offset

    def dynamic_binary_code(self, digest, offset):
        code = (
            (digest[offset] & 0x7F) << 24
            | (digest[offset + 1] & 0xFF) << 16
            | (digest[offset + 2] & 0xFF) << 8
            | (digest[offset + 3] & 0xFF)
        )
        return code


class TOTP(OTP):
    def __init__(self, *, t0=0, time_step=30, **kwargs):
        super().__init__(**kwargs)
        self.t0 = t0
        self.time_step = time_step

    def verify(self, submitted_otp):
        verified = False
        for no_time_step in self.get_no_time_steps():
            otp = self.generate(msg=no_time_step)
            if constant_compare(otp, str(submitted_otp)):
                verified = True
        return verified

    def get_no_time_steps(self):
        current_time = time.time()
        steps = []
        for delay in range(-self.network_delay, self.network_delay + 1):
            time_ = current_time + (delay * self.time_step)
            no_time_step = math.floor((time_ - self.t0) / self.time_step)
            steps.append(no_time_step.to_bytes(length=8, byteorder="big"))
        return steps
