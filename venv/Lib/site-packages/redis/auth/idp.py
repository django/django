from abc import ABC, abstractmethod

from redis.auth.token import TokenInterface

"""
This interface is the facade of an identity provider
"""


class IdentityProviderInterface(ABC):
    """
    Receive a token from the identity provider.
    Receiving a token only works when being authenticated.
    """

    @abstractmethod
    def request_token(self, force_refresh=False) -> TokenInterface:
        pass


class IdentityProviderConfigInterface(ABC):
    """
    Configuration class that provides a configured identity provider.
    """

    @abstractmethod
    def get_provider(self) -> IdentityProviderInterface:
        pass
