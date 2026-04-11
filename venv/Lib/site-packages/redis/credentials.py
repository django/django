import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class CredentialProvider:
    """
    Credentials Provider.
    """

    def get_credentials(self) -> Union[Tuple[str], Tuple[str, str]]:
        raise NotImplementedError("get_credentials must be implemented")

    async def get_credentials_async(self) -> Union[Tuple[str], Tuple[str, str]]:
        logger.warning(
            "This method is added for backward compatability. "
            "Please override it in your implementation."
        )
        return self.get_credentials()


class StreamingCredentialProvider(CredentialProvider, ABC):
    """
    Credential provider that streams credentials in the background.
    """

    @abstractmethod
    def on_next(self, callback: Callable[[Any], None]):
        """
        Specifies the callback that should be invoked
        when the next credentials will be retrieved.

        :param callback: Callback with
        :return:
        """
        pass

    @abstractmethod
    def on_error(self, callback: Callable[[Exception], None]):
        pass

    @abstractmethod
    def is_streaming(self) -> bool:
        pass


class UsernamePasswordCredentialProvider(CredentialProvider):
    """
    Simple implementation of CredentialProvider that just wraps static
    username and password.
    """

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.username = username or ""
        self.password = password or ""

    def get_credentials(self):
        if self.username:
            return self.username, self.password
        return (self.password,)

    async def get_credentials_async(self) -> Union[Tuple[str], Tuple[str, str]]:
        return self.get_credentials()
