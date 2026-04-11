from abc import ABC, abstractmethod
from typing import Optional

from redis._parsers.commands import (
    CommandPolicies,
    CommandsParser,
    PolicyRecords,
    RequestPolicy,
    ResponsePolicy,
)

STATIC_POLICIES: PolicyRecords = {
    "ft": {
        "explaincli": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "suglen": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYED,
            response_policy=ResponsePolicy.DEFAULT_KEYED,
        ),
        "profile": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "dropindex": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "aliasupdate": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "alter": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "aggregate": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "syndump": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "create": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "explain": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "sugget": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYED,
            response_policy=ResponsePolicy.DEFAULT_KEYED,
        ),
        "dictdel": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "aliasadd": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "dictadd": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "synupdate": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "drop": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "info": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "sugadd": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYED,
            response_policy=ResponsePolicy.DEFAULT_KEYED,
        ),
        "dictdump": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "cursor": CommandPolicies(
            request_policy=RequestPolicy.SPECIAL,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "search": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "tagvals": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "aliasdel": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
        "sugdel": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYED,
            response_policy=ResponsePolicy.DEFAULT_KEYED,
        ),
        "spellcheck": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
    },
    "core": {
        "command": CommandPolicies(
            request_policy=RequestPolicy.DEFAULT_KEYLESS,
            response_policy=ResponsePolicy.DEFAULT_KEYLESS,
        ),
    },
}


class PolicyResolver(ABC):
    @abstractmethod
    def resolve(self, command_name: str) -> Optional[CommandPolicies]:
        """
        Resolves the command name and determines the associated command policies.

        Args:
            command_name: The name of the command to resolve.

        Returns:
            CommandPolicies: The policies associated with the specified command.
        """
        pass

    @abstractmethod
    def with_fallback(self, fallback: "PolicyResolver") -> "PolicyResolver":
        """
        Factory method to instantiate a policy resolver with a fallback resolver.

        Args:
            fallback: Fallback resolver

        Returns:
            PolicyResolver: Returns a new policy resolver with the specified fallback resolver.
        """
        pass


class AsyncPolicyResolver(ABC):
    @abstractmethod
    async def resolve(self, command_name: str) -> Optional[CommandPolicies]:
        """
        Resolves the command name and determines the associated command policies.

        Args:
            command_name: The name of the command to resolve.

        Returns:
            CommandPolicies: The policies associated with the specified command.
        """
        pass

    @abstractmethod
    def with_fallback(self, fallback: "AsyncPolicyResolver") -> "AsyncPolicyResolver":
        """
        Factory method to instantiate an async policy resolver with a fallback resolver.

        Args:
            fallback: Fallback resolver

        Returns:
            AsyncPolicyResolver: Returns a new policy resolver with the specified fallback resolver.
        """
        pass


class BasePolicyResolver(PolicyResolver):
    """
    Base class for policy resolvers.
    """

    def __init__(
        self, policies: PolicyRecords, fallback: Optional[PolicyResolver] = None
    ) -> None:
        self._policies = policies
        self._fallback = fallback

    def resolve(self, command_name: str) -> Optional[CommandPolicies]:
        parts = command_name.split(".")

        if len(parts) > 2:
            raise ValueError(f"Wrong command or module name: {command_name}")

        module, command = parts if len(parts) == 2 else ("core", parts[0])

        if self._policies.get(module, None) is None:
            if self._fallback is not None:
                return self._fallback.resolve(command_name)
            else:
                return None

        if self._policies.get(module).get(command, None) is None:
            if self._fallback is not None:
                return self._fallback.resolve(command_name)
            else:
                return None

        return self._policies.get(module).get(command)

    @abstractmethod
    def with_fallback(self, fallback: "PolicyResolver") -> "PolicyResolver":
        pass


class AsyncBasePolicyResolver(AsyncPolicyResolver):
    """
    Async base class for policy resolvers.
    """

    def __init__(
        self, policies: PolicyRecords, fallback: Optional[AsyncPolicyResolver] = None
    ) -> None:
        self._policies = policies
        self._fallback = fallback

    async def resolve(self, command_name: str) -> Optional[CommandPolicies]:
        parts = command_name.split(".")

        if len(parts) > 2:
            raise ValueError(f"Wrong command or module name: {command_name}")

        module, command = parts if len(parts) == 2 else ("core", parts[0])

        if self._policies.get(module, None) is None:
            if self._fallback is not None:
                return await self._fallback.resolve(command_name)
            else:
                return None

        if self._policies.get(module).get(command, None) is None:
            if self._fallback is not None:
                return await self._fallback.resolve(command_name)
            else:
                return None

        return self._policies.get(module).get(command)

    @abstractmethod
    def with_fallback(self, fallback: "AsyncPolicyResolver") -> "AsyncPolicyResolver":
        pass


class DynamicPolicyResolver(BasePolicyResolver):
    """
    Resolves policy dynamically based on the COMMAND output.
    """

    def __init__(
        self, commands_parser: CommandsParser, fallback: Optional[PolicyResolver] = None
    ) -> None:
        """
        Parameters:
            commands_parser (CommandsParser): COMMAND output parser.
            fallback (Optional[PolicyResolver]): An optional resolver to be used when the
                primary policies cannot handle a specific request.
        """
        self._commands_parser = commands_parser
        super().__init__(commands_parser.get_command_policies(), fallback)

    def with_fallback(self, fallback: "PolicyResolver") -> "PolicyResolver":
        return DynamicPolicyResolver(self._commands_parser, fallback)


class StaticPolicyResolver(BasePolicyResolver):
    """
    Resolves policy from a static list of policy records.
    """

    def __init__(self, fallback: Optional[PolicyResolver] = None) -> None:
        """
        Parameters:
            fallback (Optional[PolicyResolver]): An optional fallback policy resolver
            used for resolving policies if static policies are inadequate.
        """
        super().__init__(STATIC_POLICIES, fallback)

    def with_fallback(self, fallback: "PolicyResolver") -> "PolicyResolver":
        return StaticPolicyResolver(fallback)


class AsyncDynamicPolicyResolver(AsyncBasePolicyResolver):
    """
    Async version of DynamicPolicyResolver.
    """

    def __init__(
        self,
        policy_records: PolicyRecords,
        fallback: Optional[AsyncPolicyResolver] = None,
    ) -> None:
        """
        Parameters:
            policy_records (PolicyRecords): Policy records.
            fallback (Optional[AsyncPolicyResolver]): An optional resolver to be used when the
                primary policies cannot handle a specific request.
        """
        super().__init__(policy_records, fallback)

    def with_fallback(self, fallback: "AsyncPolicyResolver") -> "AsyncPolicyResolver":
        return AsyncDynamicPolicyResolver(self._policies, fallback)


class AsyncStaticPolicyResolver(AsyncBasePolicyResolver):
    """
    Async version of StaticPolicyResolver.
    """

    def __init__(self, fallback: Optional[AsyncPolicyResolver] = None) -> None:
        """
        Parameters:
            fallback (Optional[AsyncPolicyResolver]): An optional fallback policy resolver
            used for resolving policies if static policies are inadequate.
        """
        super().__init__(STATIC_POLICIES, fallback)

    def with_fallback(self, fallback: "AsyncPolicyResolver") -> "AsyncPolicyResolver":
        return AsyncStaticPolicyResolver(fallback)
