from enum import Enum
from typing import TYPE_CHECKING, Any, Awaitable, Dict, Optional, Tuple, Union

from redis.exceptions import IncorrectPolicyType, RedisError, ResponseError
from redis.utils import str_if_bytes

if TYPE_CHECKING:
    from redis.asyncio.cluster import ClusterNode


class RequestPolicy(Enum):
    ALL_NODES = "all_nodes"
    ALL_SHARDS = "all_shards"
    ALL_REPLICAS = "all_replicas"
    MULTI_SHARD = "multi_shard"
    SPECIAL = "special"
    DEFAULT_KEYLESS = "default_keyless"
    DEFAULT_KEYED = "default_keyed"
    DEFAULT_NODE = "default_node"


class ResponsePolicy(Enum):
    ONE_SUCCEEDED = "one_succeeded"
    ALL_SUCCEEDED = "all_succeeded"
    AGG_LOGICAL_AND = "agg_logical_and"
    AGG_LOGICAL_OR = "agg_logical_or"
    AGG_MIN = "agg_min"
    AGG_MAX = "agg_max"
    AGG_SUM = "agg_sum"
    SPECIAL = "special"
    DEFAULT_KEYLESS = "default_keyless"
    DEFAULT_KEYED = "default_keyed"


class CommandPolicies:
    def __init__(
        self,
        request_policy: RequestPolicy = RequestPolicy.DEFAULT_KEYLESS,
        response_policy: ResponsePolicy = ResponsePolicy.DEFAULT_KEYLESS,
    ):
        self.request_policy = request_policy
        self.response_policy = response_policy


PolicyRecords = dict[str, dict[str, CommandPolicies]]


class AbstractCommandsParser:
    def _get_pubsub_keys(self, *args):
        """
        Get the keys from pubsub command.
        Although PubSub commands have predetermined key locations, they are not
        supported in the 'COMMAND's output, so the key positions are hardcoded
        in this method
        """
        if len(args) < 2:
            # The command has no keys in it
            return None
        args = [str_if_bytes(arg) for arg in args]
        command = args[0].upper()
        keys = None
        if command == "PUBSUB":
            # the second argument is a part of the command name, e.g.
            # ['PUBSUB', 'NUMSUB', 'foo'].
            pubsub_type = args[1].upper()
            if pubsub_type in ["CHANNELS", "NUMSUB", "SHARDCHANNELS", "SHARDNUMSUB"]:
                keys = args[2:]
        elif command in ["SUBSCRIBE", "PSUBSCRIBE", "UNSUBSCRIBE", "PUNSUBSCRIBE"]:
            # format example:
            # SUBSCRIBE channel [channel ...]
            keys = list(args[1:])
        elif command in ["PUBLISH", "SPUBLISH"]:
            # format example:
            # PUBLISH channel message
            keys = [args[1]]
        return keys

    def parse_subcommand(self, command, **options):
        cmd_dict = {}
        cmd_name = str_if_bytes(command[0])
        cmd_dict["name"] = cmd_name
        cmd_dict["arity"] = int(command[1])
        cmd_dict["flags"] = [str_if_bytes(flag) for flag in command[2]]
        cmd_dict["first_key_pos"] = command[3]
        cmd_dict["last_key_pos"] = command[4]
        cmd_dict["step_count"] = command[5]
        if len(command) > 7:
            cmd_dict["tips"] = command[7]
            cmd_dict["key_specifications"] = command[8]
            cmd_dict["subcommands"] = command[9]
        return cmd_dict


class CommandsParser(AbstractCommandsParser):
    """
    Parses Redis commands to get command keys.
    COMMAND output is used to determine key locations.
    Commands that do not have a predefined key location are flagged with
    'movablekeys', and these commands' keys are determined by the command
    'COMMAND GETKEYS'.
    """

    def __init__(self, redis_connection):
        self.commands = {}
        self.redis_connection = redis_connection
        self.initialize(self.redis_connection)

    def initialize(self, r):
        commands = r.command()
        uppercase_commands = []
        for cmd in commands:
            if any(x.isupper() for x in cmd):
                uppercase_commands.append(cmd)
        for cmd in uppercase_commands:
            commands[cmd.lower()] = commands.pop(cmd)
        self.commands = commands

    # As soon as this PR is merged into Redis, we should reimplement
    # our logic to use COMMAND INFO changes to determine the key positions
    # https://github.com/redis/redis/pull/8324
    def get_keys(self, redis_conn, *args):
        """
        Get the keys from the passed command.

        NOTE: Due to a bug in redis<7.0, this function does not work properly
        for EVAL or EVALSHA when the `numkeys` arg is 0.
         - issue: https://github.com/redis/redis/issues/9493
         - fix: https://github.com/redis/redis/pull/9733

        So, don't use this function with EVAL or EVALSHA.
        """
        if len(args) < 2:
            # The command has no keys in it
            return None

        cmd_name = args[0].lower()
        if cmd_name not in self.commands:
            # try to split the command name and to take only the main command,
            # e.g. 'memory' for 'memory usage'
            cmd_name_split = cmd_name.split()
            cmd_name = cmd_name_split[0]
            if cmd_name in self.commands:
                # save the splitted command to args
                args = cmd_name_split + list(args[1:])
            else:
                # We'll try to reinitialize the commands cache, if the engine
                # version has changed, the commands may not be current
                self.initialize(redis_conn)
                if cmd_name not in self.commands:
                    raise RedisError(
                        f"{cmd_name.upper()} command doesn't exist in Redis commands"
                    )

        command = self.commands.get(cmd_name)
        if "movablekeys" in command["flags"]:
            keys = self._get_moveable_keys(redis_conn, *args)
        elif "pubsub" in command["flags"] or command["name"] == "pubsub":
            keys = self._get_pubsub_keys(*args)
        else:
            if (
                command["step_count"] == 0
                and command["first_key_pos"] == 0
                and command["last_key_pos"] == 0
            ):
                is_subcmd = False
                if "subcommands" in command:
                    subcmd_name = f"{cmd_name}|{args[1].lower()}"
                    for subcmd in command["subcommands"]:
                        if str_if_bytes(subcmd[0]) == subcmd_name:
                            command = self.parse_subcommand(subcmd)

                            if command["first_key_pos"] > 0:
                                is_subcmd = True

                # The command doesn't have keys in it
                if not is_subcmd:
                    return None
            last_key_pos = command["last_key_pos"]
            if last_key_pos < 0:
                last_key_pos = len(args) - abs(last_key_pos)
            keys_pos = list(
                range(command["first_key_pos"], last_key_pos + 1, command["step_count"])
            )
            keys = [args[pos] for pos in keys_pos]

        return keys

    def _get_moveable_keys(self, redis_conn, *args):
        """
        NOTE: Due to a bug in redis<7.0, this function does not work properly
        for EVAL or EVALSHA when the `numkeys` arg is 0.
         - issue: https://github.com/redis/redis/issues/9493
         - fix: https://github.com/redis/redis/pull/9733

        So, don't use this function with EVAL or EVALSHA.
        """
        # The command name should be splitted into separate arguments,
        # e.g. 'MEMORY USAGE' will be splitted into ['MEMORY', 'USAGE']
        pieces = args[0].split() + list(args[1:])
        try:
            keys = redis_conn.execute_command("COMMAND GETKEYS", *pieces)
        except ResponseError as e:
            message = e.__str__()
            if (
                "Invalid arguments" in message
                or "The command has no key arguments" in message
            ):
                return None
            else:
                raise e
        return keys

    def _is_keyless_command(
        self, command_name: str, subcommand_name: Optional[str] = None
    ) -> bool:
        """
        Determines whether a given command or subcommand is considered "keyless".

        A keyless command does not operate on specific keys, which is determined based
        on the first key position in the command or subcommand details. If the command
        or subcommand's first key position is zero or negative, it is treated as keyless.

        Parameters:
            command_name: str
                The name of the command to check.
            subcommand_name: Optional[str], default=None
                The name of the subcommand to check, if applicable. If not provided,
                the check is performed only on the command.

        Returns:
            bool
                True if the specified command or subcommand is considered keyless,
                False otherwise.

        Raises:
            ValueError
                If the specified subcommand is not found within the command or the
                specified command does not exist in the available commands.
        """
        if subcommand_name:
            for subcommand in self.commands.get(command_name)["subcommands"]:
                if str_if_bytes(subcommand[0]) == subcommand_name:
                    parsed_subcmd = self.parse_subcommand(subcommand)
                    return parsed_subcmd["first_key_pos"] <= 0
            raise ValueError(
                f"Subcommand {subcommand_name} not found in command {command_name}"
            )
        else:
            command_details = self.commands.get(command_name, None)
            if command_details is not None:
                return command_details["first_key_pos"] <= 0

            raise ValueError(f"Command {command_name} not found in commands")

    def get_command_policies(self) -> PolicyRecords:
        """
        Retrieve and process the command policies for all commands and subcommands.

        This method traverses through commands and subcommands, extracting policy details
        from associated data structures and constructing a dictionary of commands with their
        associated policies. It supports nested data structures and handles both main commands
        and their subcommands.

        Returns:
            PolicyRecords: A collection of commands and subcommands associated with their
            respective policies.

        Raises:
            IncorrectPolicyType: If an invalid policy type is encountered during policy extraction.
        """
        command_with_policies = {}

        def extract_policies(data, module_name, command_name):
            """
            Recursively extract policies from nested data structures.

            Args:
                data: The data structure to search (can be list, dict, str, bytes, etc.)
                command_name: The command name to associate with found policies
            """
            if isinstance(data, (str, bytes)):
                # Decode bytes to string if needed
                policy = str_if_bytes(data.decode())

                # Check if this is a policy string
                if policy.startswith("request_policy") or policy.startswith(
                    "response_policy"
                ):
                    if policy.startswith("request_policy"):
                        policy_type = policy.split(":")[1]

                        try:
                            command_with_policies[module_name][
                                command_name
                            ].request_policy = RequestPolicy(policy_type)
                        except ValueError:
                            raise IncorrectPolicyType(
                                f"Incorrect request policy type: {policy_type}"
                            )

                    if policy.startswith("response_policy"):
                        policy_type = policy.split(":")[1]

                        try:
                            command_with_policies[module_name][
                                command_name
                            ].response_policy = ResponsePolicy(policy_type)
                        except ValueError:
                            raise IncorrectPolicyType(
                                f"Incorrect response policy type: {policy_type}"
                            )

            elif isinstance(data, list):
                # For lists, recursively process each element
                for item in data:
                    extract_policies(item, module_name, command_name)

            elif isinstance(data, dict):
                # For dictionaries, recursively process each value
                for value in data.values():
                    extract_policies(value, module_name, command_name)

        for command, details in self.commands.items():
            # Check whether the command has keys
            is_keyless = self._is_keyless_command(command)

            if is_keyless:
                default_request_policy = RequestPolicy.DEFAULT_KEYLESS
                default_response_policy = ResponsePolicy.DEFAULT_KEYLESS
            else:
                default_request_policy = RequestPolicy.DEFAULT_KEYED
                default_response_policy = ResponsePolicy.DEFAULT_KEYED

            # Check if it's a core or module command
            split_name = command.split(".")

            if len(split_name) > 1:
                module_name = split_name[0]
                command_name = split_name[1]
            else:
                module_name = "core"
                command_name = split_name[0]

            # Create a CommandPolicies object with default policies on the new command.
            if command_with_policies.get(module_name, None) is None:
                command_with_policies[module_name] = {
                    command_name: CommandPolicies(
                        request_policy=default_request_policy,
                        response_policy=default_response_policy,
                    )
                }
            else:
                command_with_policies[module_name][command_name] = CommandPolicies(
                    request_policy=default_request_policy,
                    response_policy=default_response_policy,
                )

            tips = details.get("tips")
            subcommands = details.get("subcommands")

            # Process tips for the main command
            if tips:
                extract_policies(tips, module_name, command_name)

            # Process subcommands
            if subcommands:
                for subcommand_details in subcommands:
                    # Get the subcommand name (first element)
                    subcmd_name = subcommand_details[0]
                    if isinstance(subcmd_name, bytes):
                        subcmd_name = subcmd_name.decode()

                    # Check whether the subcommand has keys
                    is_keyless = self._is_keyless_command(command, subcmd_name)

                    if is_keyless:
                        default_request_policy = RequestPolicy.DEFAULT_KEYLESS
                        default_response_policy = ResponsePolicy.DEFAULT_KEYLESS
                    else:
                        default_request_policy = RequestPolicy.DEFAULT_KEYED
                        default_response_policy = ResponsePolicy.DEFAULT_KEYED

                    subcmd_name = subcmd_name.replace("|", " ")

                    # Create a CommandPolicies object with default policies on the new command.
                    command_with_policies[module_name][subcmd_name] = CommandPolicies(
                        request_policy=default_request_policy,
                        response_policy=default_response_policy,
                    )

                    # Recursively extract policies from the rest of the subcommand details
                    for subcommand_detail in subcommand_details[1:]:
                        extract_policies(subcommand_detail, module_name, subcmd_name)

        return command_with_policies


class AsyncCommandsParser(AbstractCommandsParser):
    """
    Parses Redis commands to get command keys.

    COMMAND output is used to determine key locations.
    Commands that do not have a predefined key location are flagged with 'movablekeys',
    and these commands' keys are determined by the command 'COMMAND GETKEYS'.

    NOTE: Due to a bug in redis<7.0, this does not work properly
    for EVAL or EVALSHA when the `numkeys` arg is 0.
     - issue: https://github.com/redis/redis/issues/9493
     - fix: https://github.com/redis/redis/pull/9733

    So, don't use this with EVAL or EVALSHA.
    """

    __slots__ = ("commands", "node")

    def __init__(self) -> None:
        self.commands: Dict[str, Union[int, Dict[str, Any]]] = {}

    async def initialize(self, node: Optional["ClusterNode"] = None) -> None:
        if node:
            self.node = node

        commands = await self.node.execute_command("COMMAND")
        self.commands = {cmd.lower(): command for cmd, command in commands.items()}

    # As soon as this PR is merged into Redis, we should reimplement
    # our logic to use COMMAND INFO changes to determine the key positions
    # https://github.com/redis/redis/pull/8324
    async def get_keys(self, *args: Any) -> Optional[Tuple[str, ...]]:
        """
        Get the keys from the passed command.

        NOTE: Due to a bug in redis<7.0, this function does not work properly
        for EVAL or EVALSHA when the `numkeys` arg is 0.
         - issue: https://github.com/redis/redis/issues/9493
         - fix: https://github.com/redis/redis/pull/9733

        So, don't use this function with EVAL or EVALSHA.
        """
        if len(args) < 2:
            # The command has no keys in it
            return None

        cmd_name = args[0].lower()
        if cmd_name not in self.commands:
            # try to split the command name and to take only the main command,
            # e.g. 'memory' for 'memory usage'
            cmd_name_split = cmd_name.split()
            cmd_name = cmd_name_split[0]
            if cmd_name in self.commands:
                # save the splitted command to args
                args = cmd_name_split + list(args[1:])
            else:
                # We'll try to reinitialize the commands cache, if the engine
                # version has changed, the commands may not be current
                await self.initialize()
                if cmd_name not in self.commands:
                    raise RedisError(
                        f"{cmd_name.upper()} command doesn't exist in Redis commands"
                    )

        command = self.commands.get(cmd_name)
        if "movablekeys" in command["flags"]:
            keys = await self._get_moveable_keys(*args)
        elif "pubsub" in command["flags"] or command["name"] == "pubsub":
            keys = self._get_pubsub_keys(*args)
        else:
            if (
                command["step_count"] == 0
                and command["first_key_pos"] == 0
                and command["last_key_pos"] == 0
            ):
                is_subcmd = False
                if "subcommands" in command:
                    subcmd_name = f"{cmd_name}|{args[1].lower()}"
                    for subcmd in command["subcommands"]:
                        if str_if_bytes(subcmd[0]) == subcmd_name:
                            command = self.parse_subcommand(subcmd)

                            if command["first_key_pos"] > 0:
                                is_subcmd = True

                # The command doesn't have keys in it
                if not is_subcmd:
                    return None
            last_key_pos = command["last_key_pos"]
            if last_key_pos < 0:
                last_key_pos = len(args) - abs(last_key_pos)
            keys_pos = list(
                range(command["first_key_pos"], last_key_pos + 1, command["step_count"])
            )
            keys = [args[pos] for pos in keys_pos]

        return keys

    async def _get_moveable_keys(self, *args: Any) -> Optional[Tuple[str, ...]]:
        try:
            keys = await self.node.execute_command("COMMAND GETKEYS", *args)
        except ResponseError as e:
            message = e.__str__()
            if (
                "Invalid arguments" in message
                or "The command has no key arguments" in message
            ):
                return None
            else:
                raise e
        return keys

    async def _is_keyless_command(
        self, command_name: str, subcommand_name: Optional[str] = None
    ) -> bool:
        """
        Determines whether a given command or subcommand is considered "keyless".

        A keyless command does not operate on specific keys, which is determined based
        on the first key position in the command or subcommand details. If the command
        or subcommand's first key position is zero or negative, it is treated as keyless.

        Parameters:
            command_name: str
                The name of the command to check.
            subcommand_name: Optional[str], default=None
                The name of the subcommand to check, if applicable. If not provided,
                the check is performed only on the command.

        Returns:
            bool
                True if the specified command or subcommand is considered keyless,
                False otherwise.

        Raises:
            ValueError
                If the specified subcommand is not found within the command or the
                specified command does not exist in the available commands.
        """
        if subcommand_name:
            for subcommand in self.commands.get(command_name)["subcommands"]:
                if str_if_bytes(subcommand[0]) == subcommand_name:
                    parsed_subcmd = self.parse_subcommand(subcommand)
                    return parsed_subcmd["first_key_pos"] <= 0
            raise ValueError(
                f"Subcommand {subcommand_name} not found in command {command_name}"
            )
        else:
            command_details = self.commands.get(command_name, None)
            if command_details is not None:
                return command_details["first_key_pos"] <= 0

            raise ValueError(f"Command {command_name} not found in commands")

    async def get_command_policies(self) -> Awaitable[PolicyRecords]:
        """
        Retrieve and process the command policies for all commands and subcommands.

        This method traverses through commands and subcommands, extracting policy details
        from associated data structures and constructing a dictionary of commands with their
        associated policies. It supports nested data structures and handles both main commands
        and their subcommands.

        Returns:
            PolicyRecords: A collection of commands and subcommands associated with their
            respective policies.

        Raises:
            IncorrectPolicyType: If an invalid policy type is encountered during policy extraction.
        """
        command_with_policies = {}

        def extract_policies(data, module_name, command_name):
            """
            Recursively extract policies from nested data structures.

            Args:
                data: The data structure to search (can be list, dict, str, bytes, etc.)
                command_name: The command name to associate with found policies
            """
            if isinstance(data, (str, bytes)):
                # Decode bytes to string if needed
                policy = str_if_bytes(data.decode())

                # Check if this is a policy string
                if policy.startswith("request_policy") or policy.startswith(
                    "response_policy"
                ):
                    if policy.startswith("request_policy"):
                        policy_type = policy.split(":")[1]

                        try:
                            command_with_policies[module_name][
                                command_name
                            ].request_policy = RequestPolicy(policy_type)
                        except ValueError:
                            raise IncorrectPolicyType(
                                f"Incorrect request policy type: {policy_type}"
                            )

                    if policy.startswith("response_policy"):
                        policy_type = policy.split(":")[1]

                        try:
                            command_with_policies[module_name][
                                command_name
                            ].response_policy = ResponsePolicy(policy_type)
                        except ValueError:
                            raise IncorrectPolicyType(
                                f"Incorrect response policy type: {policy_type}"
                            )

            elif isinstance(data, list):
                # For lists, recursively process each element
                for item in data:
                    extract_policies(item, module_name, command_name)

            elif isinstance(data, dict):
                # For dictionaries, recursively process each value
                for value in data.values():
                    extract_policies(value, module_name, command_name)

        for command, details in self.commands.items():
            # Check whether the command has keys
            is_keyless = await self._is_keyless_command(command)

            if is_keyless:
                default_request_policy = RequestPolicy.DEFAULT_KEYLESS
                default_response_policy = ResponsePolicy.DEFAULT_KEYLESS
            else:
                default_request_policy = RequestPolicy.DEFAULT_KEYED
                default_response_policy = ResponsePolicy.DEFAULT_KEYED

            # Check if it's a core or module command
            split_name = command.split(".")

            if len(split_name) > 1:
                module_name = split_name[0]
                command_name = split_name[1]
            else:
                module_name = "core"
                command_name = split_name[0]

            # Create a CommandPolicies object with default policies on the new command.
            if command_with_policies.get(module_name, None) is None:
                command_with_policies[module_name] = {
                    command_name: CommandPolicies(
                        request_policy=default_request_policy,
                        response_policy=default_response_policy,
                    )
                }
            else:
                command_with_policies[module_name][command_name] = CommandPolicies(
                    request_policy=default_request_policy,
                    response_policy=default_response_policy,
                )

            tips = details.get("tips")
            subcommands = details.get("subcommands")

            # Process tips for the main command
            if tips:
                extract_policies(tips, module_name, command_name)

            # Process subcommands
            if subcommands:
                for subcommand_details in subcommands:
                    # Get the subcommand name (first element)
                    subcmd_name = subcommand_details[0]
                    if isinstance(subcmd_name, bytes):
                        subcmd_name = subcmd_name.decode()

                    # Check whether the subcommand has keys
                    is_keyless = await self._is_keyless_command(command, subcmd_name)

                    if is_keyless:
                        default_request_policy = RequestPolicy.DEFAULT_KEYLESS
                        default_response_policy = ResponsePolicy.DEFAULT_KEYLESS
                    else:
                        default_request_policy = RequestPolicy.DEFAULT_KEYED
                        default_response_policy = ResponsePolicy.DEFAULT_KEYED

                    subcmd_name = subcmd_name.replace("|", " ")

                    # Create a CommandPolicies object with default policies on the new command.
                    command_with_policies[module_name][subcmd_name] = CommandPolicies(
                        request_policy=default_request_policy,
                        response_policy=default_response_policy,
                    )

                    # Recursively extract policies from the rest of the subcommand details
                    for subcommand_detail in subcommand_details[1:]:
                        extract_policies(subcommand_detail, module_name, subcmd_name)

        return command_with_policies
