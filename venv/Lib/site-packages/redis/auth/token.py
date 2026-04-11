from abc import ABC, abstractmethod
from datetime import datetime, timezone

from redis.auth.err import InvalidTokenSchemaErr


class TokenInterface(ABC):
    @abstractmethod
    def is_expired(self) -> bool:
        pass

    @abstractmethod
    def ttl(self) -> float:
        pass

    @abstractmethod
    def try_get(self, key: str) -> str:
        pass

    @abstractmethod
    def get_value(self) -> str:
        pass

    @abstractmethod
    def get_expires_at_ms(self) -> float:
        pass

    @abstractmethod
    def get_received_at_ms(self) -> float:
        pass


class TokenResponse:
    def __init__(self, token: TokenInterface):
        self._token = token

    def get_token(self) -> TokenInterface:
        return self._token

    def get_ttl_ms(self) -> float:
        return self._token.get_expires_at_ms() - self._token.get_received_at_ms()


class SimpleToken(TokenInterface):
    def __init__(
        self, value: str, expires_at_ms: float, received_at_ms: float, claims: dict
    ) -> None:
        self.value = value
        self.expires_at = expires_at_ms
        self.received_at = received_at_ms
        self.claims = claims

    def ttl(self) -> float:
        if self.expires_at == -1:
            return -1

        return self.expires_at - (datetime.now(timezone.utc).timestamp() * 1000)

    def is_expired(self) -> bool:
        if self.expires_at == -1:
            return False

        return self.ttl() <= 0

    def try_get(self, key: str) -> str:
        return self.claims.get(key)

    def get_value(self) -> str:
        return self.value

    def get_expires_at_ms(self) -> float:
        return self.expires_at

    def get_received_at_ms(self) -> float:
        return self.received_at


class JWToken(TokenInterface):
    REQUIRED_FIELDS = {"exp"}

    def __init__(self, token: str):
        try:
            import jwt
        except ImportError as ie:
            raise ImportError(
                f"The PyJWT library is required for {self.__class__.__name__}.",
            ) from ie
        self._value = token
        self._decoded = jwt.decode(
            self._value,
            options={"verify_signature": False},
            algorithms=[jwt.get_unverified_header(self._value).get("alg")],
        )
        self._validate_token()

    def is_expired(self) -> bool:
        exp = self._decoded["exp"]
        if exp == -1:
            return False

        return (
            self._decoded["exp"] * 1000 <= datetime.now(timezone.utc).timestamp() * 1000
        )

    def ttl(self) -> float:
        exp = self._decoded["exp"]
        if exp == -1:
            return -1

        return (
            self._decoded["exp"] * 1000 - datetime.now(timezone.utc).timestamp() * 1000
        )

    def try_get(self, key: str) -> str:
        return self._decoded.get(key)

    def get_value(self) -> str:
        return self._value

    def get_expires_at_ms(self) -> float:
        return float(self._decoded["exp"] * 1000)

    def get_received_at_ms(self) -> float:
        return datetime.now(timezone.utc).timestamp() * 1000

    def _validate_token(self):
        actual_fields = {x for x in self._decoded.keys()}

        if len(self.REQUIRED_FIELDS - actual_fields) != 0:
            raise InvalidTokenSchemaErr(self.REQUIRED_FIELDS - actual_fields)
