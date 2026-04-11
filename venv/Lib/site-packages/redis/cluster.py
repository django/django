import logging
import random
import socket
import sys
import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from copy import copy
from enum import Enum
from itertools import chain
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Union,
)

from redis._parsers import CommandsParser, Encoder
from redis._parsers.commands import CommandPolicies, RequestPolicy, ResponsePolicy
from redis._parsers.helpers import parse_scan
from redis.backoff import ExponentialWithJitterBackoff, NoBackoff
from redis.cache import CacheConfig, CacheFactory, CacheFactoryInterface, CacheInterface
from redis.client import EMPTY_RESPONSE, CaseInsensitiveDict, PubSub, Redis
from redis.commands import READ_COMMANDS, RedisClusterCommands
from redis.commands.helpers import list_or_args
from redis.commands.policies import PolicyResolver, StaticPolicyResolver
from redis.connection import (
    Connection,
    ConnectionPool,
    parse_url,
)
from redis.crc import REDIS_CLUSTER_HASH_SLOTS, key_slot
from redis.event import (
    AfterPooledConnectionsInstantiationEvent,
    AfterPubSubConnectionInstantiationEvent,
    ClientType,
    EventDispatcher,
)
from redis.exceptions import (
    AskError,
    AuthenticationError,
    ClusterDownError,
    ClusterError,
    ConnectionError,
    CrossSlotTransactionError,
    DataError,
    ExecAbortError,
    InvalidPipelineStack,
    MaxConnectionsError,
    MovedError,
    RedisClusterException,
    RedisError,
    ResponseError,
    SlotNotCoveredError,
    TimeoutError,
    TryAgainError,
    WatchError,
)
from redis.lock import Lock
from redis.maint_notifications import (
    MaintNotificationsConfig,
    OSSMaintNotificationsHandler,
)
from redis.observability.recorder import (
    record_error_count,
    record_operation_duration,
)
from redis.retry import Retry
from redis.utils import (
    check_protocol_version,
    deprecated_args,
    deprecated_function,
    dict_merge,
    list_keys_to_dict,
    merge_result,
    safe_str,
    str_if_bytes,
    truncate_text,
)

logger = logging.getLogger(__name__)


def is_debug_log_enabled():
    return logger.isEnabledFor(logging.DEBUG)


def get_node_name(host: str, port: Union[str, int]) -> str:
    return f"{host}:{port}"


@deprecated_args(
    allowed_args=["redis_node"],
    reason="Use get_connection(redis_node) instead",
    version="5.3.0",
)
def get_connection(redis_node: Redis, *args, **options) -> Connection:
    return redis_node.connection or redis_node.connection_pool.get_connection()


def parse_scan_result(command, res, **options):
    cursors = {}
    ret = []
    for node_name, response in res.items():
        cursor, r = parse_scan(response, **options)
        cursors[node_name] = cursor
        ret += r

    return cursors, ret


def parse_pubsub_numsub(command, res, **options):
    numsub_d = OrderedDict()
    for numsub_tups in res.values():
        for channel, numsubbed in numsub_tups:
            try:
                numsub_d[channel] += numsubbed
            except KeyError:
                numsub_d[channel] = numsubbed

    ret_numsub = [(channel, numsub) for channel, numsub in numsub_d.items()]
    return ret_numsub


def parse_cluster_slots(
    resp: Any, **options: Any
) -> Dict[Tuple[int, int], Dict[str, Any]]:
    current_host = options.get("current_host", "")

    def fix_server(*args: Any) -> Tuple[str, Any]:
        return str_if_bytes(args[0]) or current_host, args[1]

    slots = {}
    for slot in resp:
        start, end, primary = slot[:3]
        replicas = slot[3:]
        slots[start, end] = {
            "primary": fix_server(*primary),
            "replicas": [fix_server(*replica) for replica in replicas],
        }

    return slots


def parse_cluster_shards(resp, **options):
    """
    Parse CLUSTER SHARDS response.
    """
    if isinstance(resp[0], dict):
        return resp
    shards = []
    for x in resp:
        shard = {"slots": [], "nodes": []}
        for i in range(0, len(x[1]), 2):
            shard["slots"].append((x[1][i], (x[1][i + 1])))
        nodes = x[3]
        for node in nodes:
            dict_node = {}
            for i in range(0, len(node), 2):
                dict_node[node[i]] = node[i + 1]
            shard["nodes"].append(dict_node)
        shards.append(shard)

    return shards


def parse_cluster_myshardid(resp, **options):
    """
    Parse CLUSTER MYSHARDID response.
    """
    return resp.decode("utf-8")


PRIMARY = "primary"
REPLICA = "replica"
SLOT_ID = "slot-id"

REDIS_ALLOWED_KEYS = (
    "connection_class",
    "connection_pool",
    "connection_pool_class",
    "client_name",
    "credential_provider",
    "db",
    "decode_responses",
    "encoding",
    "encoding_errors",
    "host",
    "lib_name",
    "lib_version",
    "max_connections",
    "nodes_flag",
    "redis_connect_func",
    "password",
    "port",
    "timeout",
    "queue_class",
    "retry",
    "retry_on_timeout",
    "protocol",
    "socket_connect_timeout",
    "socket_keepalive",
    "socket_keepalive_options",
    "socket_timeout",
    "ssl",
    "ssl_ca_certs",
    "ssl_ca_data",
    "ssl_ca_path",
    "ssl_certfile",
    "ssl_cert_reqs",
    "ssl_include_verify_flags",
    "ssl_exclude_verify_flags",
    "ssl_keyfile",
    "ssl_password",
    "ssl_check_hostname",
    "unix_socket_path",
    "username",
    "cache",
    "cache_config",
    "maint_notifications_config",
)
KWARGS_DISABLED_KEYS = ("host", "port", "retry")


def cleanup_kwargs(**kwargs):
    """
    Remove unsupported or disabled keys from kwargs
    """
    connection_kwargs = {
        k: v
        for k, v in kwargs.items()
        if k in REDIS_ALLOWED_KEYS and k not in KWARGS_DISABLED_KEYS
    }

    return connection_kwargs


class MaintNotificationsAbstractRedisCluster:
    """
    Abstract class for handling maintenance notifications logic.
    This class is expected to be used as base class together with RedisCluster.

    This class is intended to be used with multiple inheritance!

    All logic related to maintenance notifications is encapsulated in this class.
    """

    def __init__(
        self,
        maint_notifications_config: Optional[MaintNotificationsConfig],
        **kwargs,
    ):
        # Initialize maintenance notifications
        is_protocol_supported = check_protocol_version(kwargs.get("protocol"), 3)

        if (
            maint_notifications_config
            and maint_notifications_config.enabled
            and not is_protocol_supported
        ):
            raise RedisError(
                "Maintenance notifications handlers on connection are only supported with RESP version 3"
            )
        if maint_notifications_config is None and is_protocol_supported:
            maint_notifications_config = MaintNotificationsConfig()

        self.maint_notifications_config = maint_notifications_config

        if self.maint_notifications_config and self.maint_notifications_config.enabled:
            self._oss_cluster_maint_notifications_handler = (
                OSSMaintNotificationsHandler(self, self.maint_notifications_config)
            )
            # Update connection kwargs for all future nodes connections
            self._update_connection_kwargs_for_maint_notifications(
                self._oss_cluster_maint_notifications_handler
            )
            # Update existing nodes connections - they are created as part of the RedisCluster constructor
            for node in self.get_nodes():
                if node.redis_connection is None:
                    continue
                node.redis_connection.connection_pool.update_maint_notifications_config(
                    self.maint_notifications_config,
                    oss_cluster_maint_notifications_handler=self._oss_cluster_maint_notifications_handler,
                )
        else:
            self._oss_cluster_maint_notifications_handler = None

    def _update_connection_kwargs_for_maint_notifications(
        self, oss_cluster_maint_notifications_handler: OSSMaintNotificationsHandler
    ):
        """
        Update the connection kwargs for all future connections.
        """
        self.nodes_manager.connection_kwargs.update(
            {
                "oss_cluster_maint_notifications_handler": oss_cluster_maint_notifications_handler,
            }
        )


class AbstractRedisCluster:
    RedisClusterRequestTTL = 16

    PRIMARIES = "primaries"
    REPLICAS = "replicas"
    ALL_NODES = "all"
    RANDOM = "random"
    DEFAULT_NODE = "default-node"

    NODE_FLAGS = {PRIMARIES, REPLICAS, ALL_NODES, RANDOM, DEFAULT_NODE}

    COMMAND_FLAGS = dict_merge(
        list_keys_to_dict(
            [
                "ACL CAT",
                "ACL DELUSER",
                "ACL DRYRUN",
                "ACL GENPASS",
                "ACL GETUSER",
                "ACL HELP",
                "ACL LIST",
                "ACL LOG",
                "ACL LOAD",
                "ACL SAVE",
                "ACL SETUSER",
                "ACL USERS",
                "ACL WHOAMI",
                "AUTH",
                "CLIENT LIST",
                "CLIENT SETINFO",
                "CLIENT SETNAME",
                "CLIENT GETNAME",
                "CONFIG SET",
                "CONFIG REWRITE",
                "CONFIG RESETSTAT",
                "TIME",
                "PUBSUB CHANNELS",
                "PUBSUB NUMPAT",
                "PUBSUB NUMSUB",
                "PUBSUB SHARDCHANNELS",
                "PUBSUB SHARDNUMSUB",
                "PING",
                "INFO",
                "SHUTDOWN",
                "KEYS",
                "DBSIZE",
                "BGSAVE",
                "SLOWLOG GET",
                "SLOWLOG LEN",
                "SLOWLOG RESET",
                "WAIT",
                "WAITAOF",
                "SAVE",
                "MEMORY PURGE",
                "MEMORY MALLOC-STATS",
                "MEMORY STATS",
                "LASTSAVE",
                "CLIENT TRACKINGINFO",
                "CLIENT PAUSE",
                "CLIENT UNPAUSE",
                "CLIENT UNBLOCK",
                "CLIENT ID",
                "CLIENT REPLY",
                "CLIENT GETREDIR",
                "CLIENT INFO",
                "CLIENT KILL",
                "READONLY",
                "CLUSTER INFO",
                "CLUSTER MEET",
                "CLUSTER MYSHARDID",
                "CLUSTER NODES",
                "CLUSTER REPLICAS",
                "CLUSTER RESET",
                "CLUSTER SET-CONFIG-EPOCH",
                "CLUSTER SLOTS",
                "CLUSTER SHARDS",
                "CLUSTER COUNT-FAILURE-REPORTS",
                "CLUSTER KEYSLOT",
                "COMMAND",
                "COMMAND COUNT",
                "COMMAND LIST",
                "COMMAND GETKEYS",
                "CONFIG GET",
                "DEBUG",
                "RANDOMKEY",
                "READONLY",
                "READWRITE",
                "TIME",
                "TFUNCTION LOAD",
                "TFUNCTION DELETE",
                "TFUNCTION LIST",
                "TFCALL",
                "TFCALLASYNC",
                "LATENCY HISTORY",
                "LATENCY LATEST",
                "LATENCY RESET",
                "MODULE LIST",
                "MODULE LOAD",
                "MODULE UNLOAD",
                "MODULE LOADEX",
            ],
            DEFAULT_NODE,
        ),
        list_keys_to_dict(
            [
                "FLUSHALL",
                "FLUSHDB",
                "FUNCTION DELETE",
                "FUNCTION FLUSH",
                "FUNCTION LIST",
                "FUNCTION LOAD",
                "FUNCTION RESTORE",
                "SCAN",
                "SCRIPT EXISTS",
                "SCRIPT FLUSH",
                "SCRIPT LOAD",
            ],
            PRIMARIES,
        ),
        list_keys_to_dict(["FUNCTION DUMP"], RANDOM),
        list_keys_to_dict(
            [
                "CLUSTER COUNTKEYSINSLOT",
                "CLUSTER DELSLOTS",
                "CLUSTER DELSLOTSRANGE",
                "CLUSTER GETKEYSINSLOT",
                "CLUSTER SETSLOT",
            ],
            SLOT_ID,
        ),
    )

    SEARCH_COMMANDS = (
        [
            "FT.CREATE",
            "FT.SEARCH",
            "FT.AGGREGATE",
            "FT.EXPLAIN",
            "FT.EXPLAINCLI",
            "FT,PROFILE",
            "FT.ALTER",
            "FT.DROPINDEX",
            "FT.ALIASADD",
            "FT.ALIASUPDATE",
            "FT.ALIASDEL",
            "FT.TAGVALS",
            "FT.SUGADD",
            "FT.SUGGET",
            "FT.SUGDEL",
            "FT.SUGLEN",
            "FT.SYNUPDATE",
            "FT.SYNDUMP",
            "FT.SPELLCHECK",
            "FT.DICTADD",
            "FT.DICTDEL",
            "FT.DICTDUMP",
            "FT.INFO",
            "FT._LIST",
            "FT.CONFIG",
            "FT.ADD",
            "FT.DEL",
            "FT.DROP",
            "FT.GET",
            "FT.MGET",
            "FT.SYNADD",
        ],
    )

    CLUSTER_COMMANDS_RESPONSE_CALLBACKS = {
        "CLUSTER SLOTS": parse_cluster_slots,
        "CLUSTER SHARDS": parse_cluster_shards,
        "CLUSTER MYSHARDID": parse_cluster_myshardid,
    }

    RESULT_CALLBACKS = dict_merge(
        list_keys_to_dict(["PUBSUB NUMSUB", "PUBSUB SHARDNUMSUB"], parse_pubsub_numsub),
        list_keys_to_dict(
            ["PUBSUB NUMPAT"], lambda command, res: sum(list(res.values()))
        ),
        list_keys_to_dict(
            ["KEYS", "PUBSUB CHANNELS", "PUBSUB SHARDCHANNELS"], merge_result
        ),
        list_keys_to_dict(
            [
                "PING",
                "CONFIG SET",
                "CONFIG REWRITE",
                "CONFIG RESETSTAT",
                "CLIENT SETNAME",
                "BGSAVE",
                "SLOWLOG RESET",
                "SAVE",
                "MEMORY PURGE",
                "CLIENT PAUSE",
                "CLIENT UNPAUSE",
            ],
            lambda command, res: all(res.values()) if isinstance(res, dict) else res,
        ),
        list_keys_to_dict(
            ["DBSIZE", "WAIT"],
            lambda command, res: sum(res.values()) if isinstance(res, dict) else res,
        ),
        list_keys_to_dict(
            ["CLIENT UNBLOCK"], lambda command, res: 1 if sum(res.values()) > 0 else 0
        ),
        list_keys_to_dict(["SCAN"], parse_scan_result),
        list_keys_to_dict(
            ["SCRIPT LOAD"], lambda command, res: list(res.values()).pop()
        ),
        list_keys_to_dict(
            ["SCRIPT EXISTS"], lambda command, res: [all(k) for k in zip(*res.values())]
        ),
        list_keys_to_dict(["SCRIPT FLUSH"], lambda command, res: all(res.values())),
    )

    ERRORS_ALLOW_RETRY = (
        ConnectionError,
        TimeoutError,
        ClusterDownError,
        SlotNotCoveredError,
    )

    def replace_default_node(self, target_node: "ClusterNode" = None) -> None:
        """Replace the default cluster node.
        A random cluster node will be chosen if target_node isn't passed, and primaries
        will be prioritized. The default node will not be changed if there are no other
        nodes in the cluster.

        Args:
            target_node (ClusterNode, optional): Target node to replace the default
            node. Defaults to None.
        """
        if target_node:
            self.nodes_manager.default_node = target_node
        else:
            curr_node = self.get_default_node()
            primaries = [node for node in self.get_primaries() if node != curr_node]
            if primaries:
                # Choose a primary if the cluster contains different primaries
                self.nodes_manager.default_node = random.choice(primaries)
            else:
                # Otherwise, choose a primary if the cluster contains different primaries
                replicas = [node for node in self.get_replicas() if node != curr_node]
                if replicas:
                    self.nodes_manager.default_node = random.choice(replicas)


class RedisCluster(
    AbstractRedisCluster, MaintNotificationsAbstractRedisCluster, RedisClusterCommands
):
    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> "RedisCluster":
        """
        Return a Redis client object configured from the given URL

        For example::

            redis://[[username]:[password]]@localhost:6379/0
            rediss://[[username]:[password]]@localhost:6379/0
            unix://[username@]/path/to/socket.sock?db=0[&password=password]

        Three URL schemes are supported:

        - `redis://` creates a TCP socket connection. See more at:
          <https://www.iana.org/assignments/uri-schemes/prov/redis>
        - `rediss://` creates a SSL wrapped TCP socket connection. See more at:
          <https://www.iana.org/assignments/uri-schemes/prov/rediss>
        - ``unix://``: creates a Unix Domain Socket connection.

        The username, password, hostname, path and all querystring values
        are passed through urllib.parse.unquote in order to replace any
        percent-encoded values with their corresponding characters.

        There are several ways to specify a database number. The first value
        found will be used:

            1. A ``db`` querystring option, e.g. redis://localhost?db=0
            2. If using the redis:// or rediss:// schemes, the path argument
               of the url, e.g. redis://localhost/0
            3. A ``db`` keyword argument to this function.

        If none of these options are specified, the default db=0 is used.

        All querystring options are cast to their appropriate Python types.
        Boolean arguments can be specified with string values "True"/"False"
        or "Yes"/"No". Values that cannot be properly cast cause a
        ``ValueError`` to be raised. Once parsed, the querystring arguments
        and keyword arguments are passed to the ``ConnectionPool``'s
        class initializer. In the case of conflicting arguments, querystring
        arguments always win.

        """
        return cls(url=url, **kwargs)

    @deprecated_args(
        args_to_warn=["read_from_replicas"],
        reason="Please configure the 'load_balancing_strategy' instead",
        version="5.3.0",
    )
    @deprecated_args(
        args_to_warn=[
            "cluster_error_retry_attempts",
        ],
        reason="Please configure the 'retry' object instead",
        version="6.0.0",
    )
    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 6379,
        startup_nodes: Optional[List["ClusterNode"]] = None,
        cluster_error_retry_attempts: int = 3,
        retry: Optional["Retry"] = None,
        require_full_coverage: bool = True,
        reinitialize_steps: int = 5,
        read_from_replicas: bool = False,
        load_balancing_strategy: Optional["LoadBalancingStrategy"] = None,
        dynamic_startup_nodes: bool = True,
        url: Optional[str] = None,
        address_remap: Optional[Callable[[Tuple[str, int]], Tuple[str, int]]] = None,
        cache: Optional[CacheInterface] = None,
        cache_config: Optional[CacheConfig] = None,
        event_dispatcher: Optional[EventDispatcher] = None,
        policy_resolver: PolicyResolver = StaticPolicyResolver(),
        maint_notifications_config: Optional[MaintNotificationsConfig] = None,
        **kwargs,
    ):
        """
        Initialize a new RedisCluster client.

        :param startup_nodes:
            List of nodes from which initial bootstrapping can be done
        :param host:
            Can be used to point to a startup node
        :param port:
            Can be used to point to a startup node
        :param require_full_coverage:
            When set to False (default value): the client will not require a
            full coverage of the slots. However, if not all slots are covered,
            and at least one node has 'cluster-require-full-coverage' set to
            'yes,' the server will throw a ClusterDownError for some key-based
            commands. See -
            https://redis.io/topics/cluster-tutorial#redis-cluster-configuration-parameters
            When set to True: all slots must be covered to construct the
            cluster client. If not all slots are covered, RedisClusterException
            will be thrown.
        :param read_from_replicas:
            @deprecated - please use load_balancing_strategy instead
            Enable read from replicas in READONLY mode. You can read possibly
            stale data.
            When set to true, read commands will be assigned between the
            primary and its replications in a Round-Robin manner.
        :param load_balancing_strategy:
            Enable read from replicas in READONLY mode and defines the load balancing
            strategy that will be used for cluster node selection.
            The data read from replicas is eventually consistent with the data in primary nodes.
        :param dynamic_startup_nodes:
            Set the RedisCluster's startup nodes to all of the discovered nodes.
            If true (default value), the cluster's discovered nodes will be used to
            determine the cluster nodes-slots mapping in the next topology refresh.
            It will remove the initial passed startup nodes if their endpoints aren't
            listed in the CLUSTER SLOTS output.
            If you use dynamic DNS endpoints for startup nodes but CLUSTER SLOTS lists
            specific IP addresses, it is best to set it to false.
        :param cluster_error_retry_attempts:
            @deprecated - Please configure the 'retry' object instead
            In case 'retry' object is set - this argument is ignored!

            Number of times to retry before raising an error when
            :class:`~.TimeoutError` or :class:`~.ConnectionError`, :class:`~.SlotNotCoveredError` or
            :class:`~.ClusterDownError` are encountered
        :param retry:
            A retry object that defines the retry strategy and the number of
            retries for the cluster client.
            In current implementation for the cluster client (starting form redis-py version 6.0.0)
            the retry object is not yet fully utilized, instead it is used just to determine
            the number of retries for the cluster client.
            In the future releases the retry object will be used to handle the cluster client retries!
        :param reinitialize_steps:
            Specifies the number of MOVED errors that need to occur before
            reinitializing the whole cluster topology. If a MOVED error occurs
            and the cluster does not need to be reinitialized on this current
            error handling, only the MOVED slot will be patched with the
            redirected node.
            To reinitialize the cluster on every MOVED error, set
            reinitialize_steps to 1.
            To avoid reinitializing the cluster on moved errors, set
            reinitialize_steps to 0.
        :param address_remap:
            An optional callable which, when provided with an internal network
            address of a node, e.g. a `(host, port)` tuple, will return the address
            where the node is reachable.  This can be used to map the addresses at
            which the nodes _think_ they are, to addresses at which a client may
            reach them, such as when they sit behind a proxy.

        :param maint_notifications_config:
            Configures the nodes connections to support maintenance notifications - see
            `redis.maint_notifications.MaintNotificationsConfig` for details.
            Only supported with RESP3.
            If not provided and protocol is RESP3, the maintenance notifications
            will be enabled by default (logic is included in the NodesManager
            initialization).
        :**kwargs:
            Extra arguments that will be sent into Redis instance when created
            (See Official redis-py doc for supported kwargs - the only limitation
            is that you can't provide 'retry' object as part of kwargs.
            [https://github.com/andymccurdy/redis-py/blob/master/redis/client.py])
            Some kwargs are not supported and will raise a
            RedisClusterException:
                - db (Redis do not support database SELECT in cluster mode)

        """
        if startup_nodes is None:
            startup_nodes = []

        if "db" in kwargs:
            # Argument 'db' is not possible to use in cluster mode
            raise RedisClusterException(
                "Argument 'db' is not possible to use in cluster mode"
            )

        if "retry" in kwargs:
            # Argument 'retry' is not possible to be used in kwargs when in cluster mode
            # the kwargs are set to the lower level connections to the cluster nodes
            # and there we provide retry configuration without retries allowed.
            # The retries should be handled on cluster client level.
            raise RedisClusterException(
                "The 'retry' argument cannot be used in kwargs when running in cluster mode."
            )

        # Get the startup node/s
        from_url = False
        if url is not None:
            from_url = True
            url_options = parse_url(url)
            if "path" in url_options:
                raise RedisClusterException(
                    "RedisCluster does not currently support Unix Domain "
                    "Socket connections"
                )
            if "db" in url_options and url_options["db"] != 0:
                # Argument 'db' is not possible to use in cluster mode
                raise RedisClusterException(
                    "A ``db`` querystring option can only be 0 in cluster mode"
                )
            kwargs.update(url_options)
            host = kwargs.get("host")
            port = kwargs.get("port", port)
            startup_nodes.append(ClusterNode(host, port))
        elif host is not None and port is not None:
            startup_nodes.append(ClusterNode(host, port))
        elif len(startup_nodes) == 0:
            # No startup node was provided
            raise RedisClusterException(
                "RedisCluster requires at least one node to discover the "
                "cluster. Please provide one of the followings:\n"
                "1. host and port, for example:\n"
                " RedisCluster(host='localhost', port=6379)\n"
                "2. list of startup nodes, for example:\n"
                " RedisCluster(startup_nodes=[ClusterNode('localhost', 6379),"
                " ClusterNode('localhost', 6378)])"
            )
        # Update the connection arguments
        # Whenever a new connection is established, RedisCluster's on_connect
        # method should be run
        # If the user passed on_connect function we'll save it and run it
        # inside the RedisCluster.on_connect() function
        self.user_on_connect_func = kwargs.pop("redis_connect_func", None)
        kwargs.update({"redis_connect_func": self.on_connect})
        kwargs = cleanup_kwargs(**kwargs)
        if retry:
            self.retry = retry
        else:
            self.retry = Retry(
                backoff=ExponentialWithJitterBackoff(base=1, cap=10),
                retries=cluster_error_retry_attempts,
            )

        self.encoder = Encoder(
            kwargs.get("encoding", "utf-8"),
            kwargs.get("encoding_errors", "strict"),
            kwargs.get("decode_responses", False),
        )
        protocol = kwargs.get("protocol", None)
        if (cache_config or cache) and not check_protocol_version(protocol, 3):
            raise RedisError("Client caching is only supported with RESP version 3")

        if maint_notifications_config and not check_protocol_version(protocol, 3):
            raise RedisError(
                "Maintenance notifications are only supported with RESP version 3"
            )
        if check_protocol_version(protocol, 3) and maint_notifications_config is None:
            maint_notifications_config = MaintNotificationsConfig()

        self.command_flags = self.__class__.COMMAND_FLAGS.copy()
        self.node_flags = self.__class__.NODE_FLAGS.copy()
        self.read_from_replicas = read_from_replicas
        self.load_balancing_strategy = load_balancing_strategy
        self.reinitialize_counter = 0
        self.reinitialize_steps = reinitialize_steps
        if event_dispatcher is None:
            self._event_dispatcher = EventDispatcher()
        else:
            self._event_dispatcher = event_dispatcher
        self.startup_nodes = startup_nodes

        self.nodes_manager = NodesManager(
            startup_nodes=startup_nodes,
            from_url=from_url,
            require_full_coverage=require_full_coverage,
            dynamic_startup_nodes=dynamic_startup_nodes,
            address_remap=address_remap,
            cache=cache,
            cache_config=cache_config,
            event_dispatcher=self._event_dispatcher,
            maint_notifications_config=maint_notifications_config,
            **kwargs,
        )

        self.cluster_response_callbacks = CaseInsensitiveDict(
            self.__class__.CLUSTER_COMMANDS_RESPONSE_CALLBACKS
        )
        self.result_callbacks = CaseInsensitiveDict(self.__class__.RESULT_CALLBACKS)

        # For backward compatibility, mapping from existing policies to new one
        self._command_flags_mapping: dict[str, Union[RequestPolicy, ResponsePolicy]] = {
            self.__class__.RANDOM: RequestPolicy.DEFAULT_KEYLESS,
            self.__class__.PRIMARIES: RequestPolicy.ALL_SHARDS,
            self.__class__.ALL_NODES: RequestPolicy.ALL_NODES,
            self.__class__.REPLICAS: RequestPolicy.ALL_REPLICAS,
            self.__class__.DEFAULT_NODE: RequestPolicy.DEFAULT_NODE,
            SLOT_ID: RequestPolicy.DEFAULT_KEYED,
        }

        self._policies_callback_mapping: dict[
            Union[RequestPolicy, ResponsePolicy], Callable
        ] = {
            RequestPolicy.DEFAULT_KEYLESS: lambda command_name: [
                self.get_random_primary_or_all_nodes(command_name)
            ],
            RequestPolicy.DEFAULT_KEYED: lambda command,
            *args: self.get_nodes_from_slot(command, *args),
            RequestPolicy.DEFAULT_NODE: lambda: [self.get_default_node()],
            RequestPolicy.ALL_SHARDS: self.get_primaries,
            RequestPolicy.ALL_NODES: self.get_nodes,
            RequestPolicy.ALL_REPLICAS: self.get_replicas,
            RequestPolicy.MULTI_SHARD: lambda *args,
            **kwargs: self._split_multi_shard_command(*args, **kwargs),
            RequestPolicy.SPECIAL: self.get_special_nodes,
            ResponsePolicy.DEFAULT_KEYLESS: lambda res: res,
            ResponsePolicy.DEFAULT_KEYED: lambda res: res,
        }

        self._policy_resolver = policy_resolver
        self.commands_parser = CommandsParser(self)

        # Node where FT.AGGREGATE command is executed.
        self._aggregate_nodes = None
        self._lock = threading.RLock()

        MaintNotificationsAbstractRedisCluster.__init__(
            self, maint_notifications_config, **kwargs
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def disconnect_connection_pools(self):
        for node in self.get_nodes():
            if node.redis_connection:
                try:
                    node.redis_connection.connection_pool.disconnect()
                except OSError:
                    # Client was already disconnected. do nothing
                    pass

    def on_connect(self, connection):
        """
        Initialize the connection, authenticate and select a database and send
         READONLY if it is set during object initialization.
        """
        connection.on_connect()

        if self.read_from_replicas or self.load_balancing_strategy:
            # Sending READONLY command to server to configure connection as
            # readonly. Since each cluster node may change its server type due
            # to a failover, we should establish a READONLY connection
            # regardless of the server type. If this is a primary connection,
            # READONLY would not affect executing write commands.
            connection.send_command("READONLY")
            if str_if_bytes(connection.read_response()) != "OK":
                raise ConnectionError("READONLY command failed")

        if self.user_on_connect_func is not None:
            self.user_on_connect_func(connection)

    def get_redis_connection(self, node: "ClusterNode") -> Redis:
        if not node.redis_connection:
            with self._lock:
                if not node.redis_connection:
                    self.nodes_manager.create_redis_connections([node])
        return node.redis_connection

    def get_node(self, host=None, port=None, node_name=None):
        return self.nodes_manager.get_node(host, port, node_name)

    def get_primaries(self):
        return self.nodes_manager.get_nodes_by_server_type(PRIMARY)

    def get_replicas(self):
        return self.nodes_manager.get_nodes_by_server_type(REPLICA)

    def get_random_node(self):
        return random.choice(list(self.nodes_manager.nodes_cache.values()))

    def get_random_primary_or_all_nodes(self, command_name):
        """
        Returns random primary or all nodes depends on READONLY mode.
        """
        if self.read_from_replicas and command_name in READ_COMMANDS:
            return self.get_random_node()

        return self.get_random_primary_node()

    def get_nodes(self):
        return list(self.nodes_manager.nodes_cache.values())

    def get_node_from_key(self, key, replica=False):
        """
        Get the node that holds the key's slot.
        If replica set to True but the slot doesn't have any replicas, None is
        returned.
        """
        slot = self.keyslot(key)
        slot_cache = self.nodes_manager.slots_cache.get(slot)
        if slot_cache is None or len(slot_cache) == 0:
            raise SlotNotCoveredError(f'Slot "{slot}" is not covered by the cluster.')
        if replica and len(self.nodes_manager.slots_cache[slot]) < 2:
            return None
        elif replica:
            node_idx = 1
        else:
            # primary
            node_idx = 0

        return slot_cache[node_idx]

    def get_default_node(self):
        """
        Get the cluster's default node
        """
        return self.nodes_manager.default_node

    def get_nodes_from_slot(self, command: str, *args):
        """
        Returns a list of nodes that hold the specified keys' slots.
        """
        # get the node that holds the key's slot
        slot = self.determine_slot(*args)
        node = self.nodes_manager.get_node_from_slot(
            slot,
            self.read_from_replicas and command in READ_COMMANDS,
            self.load_balancing_strategy if command in READ_COMMANDS else None,
        )
        return [node]

    def _split_multi_shard_command(self, *args, **kwargs) -> list[dict]:
        """
        Splits the command with Multi-Shard policy, to the multiple commands
        """
        keys = self._get_command_keys(*args)
        commands = []

        for key in keys:
            commands.append(
                {
                    "args": (args[0], key),
                    "kwargs": kwargs,
                }
            )

        return commands

    def get_special_nodes(self) -> Optional[list["ClusterNode"]]:
        """
        Returns a list of nodes for commands with a special policy.
        """
        if not self._aggregate_nodes:
            raise RedisClusterException(
                "Cannot execute FT.CURSOR commands without FT.AGGREGATE"
            )

        return self._aggregate_nodes

    def get_random_primary_node(self) -> "ClusterNode":
        """
        Returns a random primary node
        """
        return random.choice(self.get_primaries())

    def _evaluate_all_succeeded(self, res):
        """
        Evaluate the result of a command with ResponsePolicy.ALL_SUCCEEDED
        """
        first_successful_response = None

        if isinstance(res, dict):
            for key, value in res.items():
                if value:
                    if first_successful_response is None:
                        first_successful_response = {key: value}
                else:
                    return {key: False}
        else:
            for response in res:
                if response:
                    if first_successful_response is None:
                        # Dynamically resolve type
                        first_successful_response = type(response)(response)
                else:
                    return type(response)(False)

        return first_successful_response

    def set_default_node(self, node):
        """
        Set the default node of the cluster.
        :param node: 'ClusterNode'
        :return True if the default node was set, else False
        """
        if node is None or self.get_node(node_name=node.name) is None:
            return False
        self.nodes_manager.default_node = node
        return True

    def set_retry(self, retry: Retry) -> None:
        self.retry = retry

    def monitor(self, target_node=None):
        """
        Returns a Monitor object for the specified target node.
        The default cluster node will be selected if no target node was
        specified.
        Monitor is useful for handling the MONITOR command to the redis server.
        next_command() method returns one command from monitor
        listen() method yields commands from monitor.
        """
        if target_node is None:
            target_node = self.get_default_node()
        if target_node.redis_connection is None:
            raise RedisClusterException(
                f"Cluster Node {target_node.name} has no redis_connection"
            )
        return target_node.redis_connection.monitor()

    def pubsub(self, node=None, host=None, port=None, **kwargs):
        """
        Allows passing a ClusterNode, or host&port, to get a pubsub instance
        connected to the specified node
        """
        return ClusterPubSub(self, node=node, host=host, port=port, **kwargs)

    def pipeline(self, transaction=None, shard_hint=None):
        """
        Cluster impl:
            Pipelines do not work in cluster mode the same way they
            do in normal mode. Create a clone of this object so
            that simulating pipelines will work correctly. Each
            command will be called directly when used and
            when calling execute() will only return the result stack.
        """
        if shard_hint:
            raise RedisClusterException("shard_hint is deprecated in cluster mode")

        return ClusterPipeline(
            nodes_manager=self.nodes_manager,
            commands_parser=self.commands_parser,
            startup_nodes=self.nodes_manager.startup_nodes,
            result_callbacks=self.result_callbacks,
            cluster_response_callbacks=self.cluster_response_callbacks,
            read_from_replicas=self.read_from_replicas,
            load_balancing_strategy=self.load_balancing_strategy,
            reinitialize_steps=self.reinitialize_steps,
            retry=self.retry,
            lock=self._lock,
            transaction=transaction,
            event_dispatcher=self._event_dispatcher,
        )

    def lock(
        self,
        name,
        timeout=None,
        sleep=0.1,
        blocking=True,
        blocking_timeout=None,
        lock_class=None,
        thread_local=True,
        raise_on_release_error: bool = True,
    ):
        """
        Return a new Lock object using key ``name`` that mimics
        the behavior of threading.Lock.

        If specified, ``timeout`` indicates a maximum life for the lock.
        By default, it will remain locked until release() is called.

        ``sleep`` indicates the amount of time to sleep per loop iteration
        when the lock is in blocking mode and another client is currently
        holding the lock.

        ``blocking`` indicates whether calling ``acquire`` should block until
        the lock has been acquired or to fail immediately, causing ``acquire``
        to return False and the lock not being acquired. Defaults to True.
        Note this value can be overridden by passing a ``blocking``
        argument to ``acquire``.

        ``blocking_timeout`` indicates the maximum amount of time in seconds to
        spend trying to acquire the lock. A value of ``None`` indicates
        continue trying forever. ``blocking_timeout`` can be specified as a
        float or integer, both representing the number of seconds to wait.

        ``lock_class`` forces the specified lock implementation. Note that as
        of redis-py 3.0, the only lock class we implement is ``Lock`` (which is
        a Lua-based lock). So, it's unlikely you'll need this parameter, unless
        you have created your own custom lock class.

        ``thread_local`` indicates whether the lock token is placed in
        thread-local storage. By default, the token is placed in thread local
        storage so that a thread only sees its token, not a token set by
        another thread. Consider the following timeline:

            time: 0, thread-1 acquires `my-lock`, with a timeout of 5 seconds.
                     thread-1 sets the token to "abc"
            time: 1, thread-2 blocks trying to acquire `my-lock` using the
                     Lock instance.
            time: 5, thread-1 has not yet completed. redis expires the lock
                     key.
            time: 5, thread-2 acquired `my-lock` now that it's available.
                     thread-2 sets the token to "xyz"
            time: 6, thread-1 finishes its work and calls release(). if the
                     token is *not* stored in thread local storage, then
                     thread-1 would see the token value as "xyz" and would be
                     able to successfully release the thread-2's lock.

        ``raise_on_release_error`` indicates whether to raise an exception when
        the lock is no longer owned when exiting the context manager. By default,
        this is True, meaning an exception will be raised. If False, the warning
        will be logged and the exception will be suppressed.

        In some use cases it's necessary to disable thread local storage. For
        example, if you have code where one thread acquires a lock and passes
        that lock instance to a worker thread to release later. If thread
        local storage isn't disabled in this case, the worker thread won't see
        the token set by the thread that acquired the lock. Our assumption
        is that these cases aren't common and as such default to using
        thread local storage."""
        if lock_class is None:
            lock_class = Lock
        return lock_class(
            self,
            name,
            timeout=timeout,
            sleep=sleep,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
            thread_local=thread_local,
            raise_on_release_error=raise_on_release_error,
        )

    def set_response_callback(self, command, callback):
        """Set a custom Response Callback"""
        self.cluster_response_callbacks[command] = callback

    def _determine_nodes(
        self, *args, request_policy: RequestPolicy, **kwargs
    ) -> List["ClusterNode"]:
        """
        Determines a nodes the command should be executed on.
        """
        command = args[0].upper()
        if len(args) >= 2 and f"{args[0]} {args[1]}".upper() in self.command_flags:
            command = f"{args[0]} {args[1]}".upper()

        nodes_flag = kwargs.pop("nodes_flag", None)
        if nodes_flag is not None:
            # nodes flag passed by the user
            command_flag = nodes_flag
        else:
            # get the nodes group for this command if it was predefined
            command_flag = self.command_flags.get(command)

        if command_flag in self._command_flags_mapping:
            request_policy = self._command_flags_mapping[command_flag]

        policy_callback = self._policies_callback_mapping[request_policy]

        if request_policy == RequestPolicy.DEFAULT_KEYED:
            nodes = policy_callback(command, *args)
        elif request_policy == RequestPolicy.MULTI_SHARD:
            nodes = policy_callback(*args, **kwargs)
        elif request_policy == RequestPolicy.DEFAULT_KEYLESS:
            nodes = policy_callback(args[0])
        else:
            nodes = policy_callback()

        if args[0].lower() == "ft.aggregate":
            self._aggregate_nodes = nodes

        return nodes

    def _should_reinitialized(self):
        # To reinitialize the cluster on every MOVED error,
        # set reinitialize_steps to 1.
        # To avoid reinitializing the cluster on moved errors, set
        # reinitialize_steps to 0.
        if self.reinitialize_steps == 0:
            return False
        else:
            return self.reinitialize_counter % self.reinitialize_steps == 0

    def keyslot(self, key):
        """
        Calculate keyslot for a given key.
        See Keys distribution model in https://redis.io/topics/cluster-spec
        """
        k = self.encoder.encode(key)
        return key_slot(k)

    def _get_command_keys(self, *args):
        """
        Get the keys in the command. If the command has no keys in in, None is
        returned.

        NOTE: Due to a bug in redis<7.0, this function does not work properly
        for EVAL or EVALSHA when the `numkeys` arg is 0.
         - issue: https://github.com/redis/redis/issues/9493
         - fix: https://github.com/redis/redis/pull/9733

        So, don't use this function with EVAL or EVALSHA.
        """
        redis_conn = self.get_default_node().redis_connection
        return self.commands_parser.get_keys(redis_conn, *args)

    def determine_slot(self, *args) -> Optional[int]:
        """
        Figure out what slot to use based on args.

        Raises a RedisClusterException if there's a missing key and we can't
            determine what slots to map the command to; or, if the keys don't
            all map to the same key slot.
        """
        command = args[0]
        if self.command_flags.get(command) == SLOT_ID:
            # The command contains the slot ID
            return args[1]

        # Get the keys in the command

        # CLIENT TRACKING is a special case.
        # It doesn't have any keys, it needs to be sent to the provided nodes
        # By default it will be sent to all nodes.
        if command.upper() == "CLIENT TRACKING":
            return None

        # EVAL and EVALSHA are common enough that it's wasteful to go to the
        # redis server to parse the keys. Besides, there is a bug in redis<7.0
        # where `self._get_command_keys()` fails anyway. So, we special case
        # EVAL/EVALSHA.
        if command.upper() in ("EVAL", "EVALSHA"):
            # command syntax: EVAL "script body" num_keys ...
            if len(args) <= 2:
                raise RedisClusterException(f"Invalid args in command: {args}")
            num_actual_keys = int(args[2])
            eval_keys = args[3 : 3 + num_actual_keys]
            # if there are 0 keys, that means the script can be run on any node
            # so we can just return a random slot
            if len(eval_keys) == 0:
                return random.randrange(0, REDIS_CLUSTER_HASH_SLOTS)
            keys = eval_keys
        else:
            keys = self._get_command_keys(*args)
            if keys is None or len(keys) == 0:
                # FCALL can call a function with 0 keys, that means the function
                #  can be run on any node so we can just return a random slot
                if command.upper() in ("FCALL", "FCALL_RO"):
                    return random.randrange(0, REDIS_CLUSTER_HASH_SLOTS)
                raise RedisClusterException(
                    "No way to dispatch this command to Redis Cluster. "
                    "Missing key.\nYou can execute the command by specifying "
                    f"target nodes.\nCommand: {args}"
                )

        # single key command
        if len(keys) == 1:
            return self.keyslot(keys[0])

        # multi-key command; we need to make sure all keys are mapped to
        # the same slot
        slots = {self.keyslot(key) for key in keys}
        if len(slots) != 1:
            raise RedisClusterException(
                f"{command} - all keys must map to the same key slot"
            )

        return slots.pop()

    def get_encoder(self):
        """
        Get the connections' encoder
        """
        return self.encoder

    def get_connection_kwargs(self):
        """
        Get the connections' key-word arguments
        """
        return self.nodes_manager.connection_kwargs

    def _is_nodes_flag(self, target_nodes):
        return isinstance(target_nodes, str) and target_nodes in self.node_flags

    def _parse_target_nodes(self, target_nodes):
        if isinstance(target_nodes, list):
            nodes = target_nodes
        elif isinstance(target_nodes, ClusterNode):
            # Supports passing a single ClusterNode as a variable
            nodes = [target_nodes]
        elif isinstance(target_nodes, dict):
            # Supports dictionaries of the format {node_name: node}.
            # It enables to execute commands with multi nodes as follows:
            # rc.cluster_save_config(rc.get_primaries())
            nodes = target_nodes.values()
        else:
            raise TypeError(
                "target_nodes type can be one of the following: "
                "node_flag (PRIMARIES, REPLICAS, RANDOM, ALL_NODES),"
                "ClusterNode, list<ClusterNode>, or dict<any, ClusterNode>. "
                f"The passed type is {type(target_nodes)}"
            )
        return nodes

    def execute_command(self, *args, **kwargs):
        return self._internal_execute_command(*args, **kwargs)

    def _internal_execute_command(self, *args, **kwargs):
        """
        Wrapper for ERRORS_ALLOW_RETRY error handling.

        It will try the number of times specified by the retries property from
        config option "self.retry" which defaults to 3 unless manually
        configured.

        If it reaches the number of times, the command will raise the exception

        Key argument :target_nodes: can be passed with the following types:
            nodes_flag: PRIMARIES, REPLICAS, ALL_NODES, RANDOM
            ClusterNode
            list<ClusterNode>
            dict<Any, ClusterNode>
        """
        target_nodes_specified = False
        is_default_node = False
        target_nodes = None
        passed_targets = kwargs.pop("target_nodes", None)
        command_policies = self._policy_resolver.resolve(args[0].lower())

        if passed_targets is not None and not self._is_nodes_flag(passed_targets):
            target_nodes = self._parse_target_nodes(passed_targets)
            target_nodes_specified = True

        if not command_policies and not target_nodes_specified:
            command = args[0].upper()
            if len(args) >= 2 and f"{args[0]} {args[1]}".upper() in self.command_flags:
                command = f"{args[0]} {args[1]}".upper()

            # We only could resolve key properties if command is not
            # in a list of pre-defined request policies
            command_flag = self.command_flags.get(command)
            if not command_flag:
                # Fallback to default policy
                if not self.get_default_node():
                    slot = None
                else:
                    slot = self.determine_slot(*args)
                if slot is None:
                    command_policies = CommandPolicies()
                else:
                    command_policies = CommandPolicies(
                        request_policy=RequestPolicy.DEFAULT_KEYED,
                        response_policy=ResponsePolicy.DEFAULT_KEYED,
                    )
            else:
                if command_flag in self._command_flags_mapping:
                    command_policies = CommandPolicies(
                        request_policy=self._command_flags_mapping[command_flag]
                    )
                else:
                    command_policies = CommandPolicies()
        elif not command_policies and target_nodes_specified:
            command_policies = CommandPolicies()

        # If an error that allows retrying was thrown, the nodes and slots
        # cache were reinitialized. We will retry executing the command with
        # the updated cluster setup only when the target nodes can be
        # determined again with the new cache tables. Therefore, when target
        # nodes were passed to this function, we cannot retry the command
        # execution since the nodes may not be valid anymore after the tables
        # were reinitialized. So in case of passed target nodes,
        # retry_attempts will be set to 0.
        retry_attempts = 0 if target_nodes_specified else self.retry.get_retries()
        # Add one for the first execution
        execute_attempts = 1 + retry_attempts
        failure_count = 0

        # Start timing for observability
        start_time = time.monotonic()

        for _ in range(execute_attempts):
            try:
                res = {}
                if not target_nodes_specified:
                    # Determine the nodes to execute the command on
                    target_nodes = self._determine_nodes(
                        *args,
                        request_policy=command_policies.request_policy,
                        nodes_flag=passed_targets,
                    )

                    if not target_nodes:
                        raise RedisClusterException(
                            f"No targets were found to execute {args} command on"
                        )
                    if (
                        len(target_nodes) == 1
                        and target_nodes[0] == self.get_default_node()
                    ):
                        is_default_node = True
                for node in target_nodes:
                    res[node.name] = self._execute_command(node, *args, **kwargs)

                    if command_policies.response_policy == ResponsePolicy.ONE_SUCCEEDED:
                        break

                # Return the processed result
                return self._process_result(
                    args[0],
                    res,
                    response_policy=command_policies.response_policy,
                    **kwargs,
                )
            except Exception as e:
                if retry_attempts > 0 and type(e) in self.__class__.ERRORS_ALLOW_RETRY:
                    if is_default_node:
                        # Replace the default cluster node
                        self.replace_default_node()
                    # The nodes and slots cache were reinitialized.
                    # Try again with the new cluster setup.
                    retry_attempts -= 1
                    failure_count += 1

                    if hasattr(e, "connection"):
                        self._emit_after_command_execution_event(
                            command_name=args[0],
                            duration_seconds=time.monotonic() - start_time,
                            connection=e.connection,
                            error=e,
                        )

                        self._emit_on_error_event(
                            error=e,
                            connection=e.connection,
                            retry_attempts=failure_count,
                        )
                    continue
                else:
                    # raise the exception
                    if hasattr(e, "connection"):
                        self._emit_on_error_event(
                            error=e,
                            connection=e.connection,
                            retry_attempts=failure_count,
                            is_internal=False,
                        )
                    raise e

    def _execute_command(self, target_node, *args, **kwargs):
        """
        Send a command to a node in the cluster
        """
        command = args[0]
        redis_node = None
        connection = None
        redirect_addr = None
        asking = False
        moved = False
        ttl = int(self.RedisClusterRequestTTL)

        # Start timing for observability
        start_time = time.monotonic()

        while ttl > 0:
            ttl -= 1
            try:
                if asking:
                    target_node = self.get_node(node_name=redirect_addr)
                elif moved:
                    # MOVED occurred and the slots cache was updated,
                    # refresh the target node
                    slot = self.determine_slot(*args)
                    target_node = self.nodes_manager.get_node_from_slot(
                        slot,
                        self.read_from_replicas and command in READ_COMMANDS,
                        self.load_balancing_strategy
                        if command in READ_COMMANDS
                        else None,
                    )
                    moved = False

                redis_node = self.get_redis_connection(target_node)
                connection = get_connection(redis_node)
                if asking:
                    connection.send_command("ASKING")
                    redis_node.parse_response(connection, "ASKING", **kwargs)
                    asking = False
                connection.send_command(*args, **kwargs)
                response = redis_node.parse_response(connection, command, **kwargs)

                # Remove keys entry, it needs only for cache.
                kwargs.pop("keys", None)

                if command in self.cluster_response_callbacks:
                    response = self.cluster_response_callbacks[command](
                        response, **kwargs
                    )

                self._emit_after_command_execution_event(
                    command_name=command,
                    duration_seconds=time.monotonic() - start_time,
                    connection=connection,
                )
                return response
            except AuthenticationError as e:
                e.connection = connection
                raise
            except MaxConnectionsError as e:
                # MaxConnectionsError indicates client-side resource exhaustion
                # (too many connections in the pool), not a node failure.
                # Don't treat this as a node failure - just re-raise the error
                # without reinitializing the cluster.
                e.connection = connection
                raise
            except (ConnectionError, TimeoutError) as e:
                # ConnectionError can also be raised if we couldn't get a
                # connection from the pool before timing out, so check that
                # this is an actual connection before attempting to disconnect.
                if connection is not None:
                    connection.disconnect()

                # Instead of setting to None, properly handle the pool
                # Get the pool safely - redis_connection could be set to None
                # by another thread between the check and access
                redis_conn = target_node.redis_connection
                if redis_conn is not None:
                    pool = redis_conn.connection_pool
                    if pool is not None:
                        with pool._lock:
                            # take care for the active connections in the pool
                            pool.update_active_connections_for_reconnect()
                            # disconnect all free connections
                            pool.disconnect_free_connections()

                # Move the failed node to the end of the cached nodes list
                self.nodes_manager.move_node_to_end_of_cached_nodes(target_node.name)

                # DON'T set redis_connection = None - keep the pool for reuse
                self.nodes_manager.initialize()
                e.connection = connection
                raise e
            except MovedError as e:
                if is_debug_log_enabled():
                    socket_address = self._extracts_socket_address(connection)
                    args_log_str = truncate_text(" ".join(map(safe_str, args)))
                    logger.debug(
                        f"MOVED error received for command {args_log_str}, on node {target_node.name}, "
                        f"and connection: {connection} using local socket address: {socket_address}, error: {e}"
                    )
                # First, we will try to patch the slots/nodes cache with the
                # redirected node output and try again. If MovedError exceeds
                # 'reinitialize_steps' number of times, we will force
                # reinitializing the tables, and then try again.
                # 'reinitialize_steps' counter will increase faster when
                # the same client object is shared between multiple threads. To
                # reduce the frequency you can set this variable in the
                # RedisCluster constructor.
                self.reinitialize_counter += 1
                if self._should_reinitialized():
                    # during this call all connections are closed or marked for disconnect,
                    # so we don't need to disconnect the changed node's connections
                    self.nodes_manager.initialize(
                        additional_startup_nodes_info=[(e.host, e.port)]
                    )
                    # Reset the counter
                    self.reinitialize_counter = 0
                else:
                    self.nodes_manager.move_slot(e)
                moved = True
                self._emit_after_command_execution_event(
                    command_name=command,
                    duration_seconds=time.monotonic() - start_time,
                    connection=connection,
                    error=e,
                )
                self._emit_on_error_event(
                    error=e,
                    connection=connection,
                )
            except TryAgainError as e:
                if is_debug_log_enabled():
                    socket_address = self._extracts_socket_address(connection)
                    args_log_str = truncate_text(" ".join(map(safe_str, args)))
                    logger.debug(
                        f"TRYAGAIN error received for command {args_log_str}, on node {target_node.name}, "
                        f"and connection: {connection} using local socket address: {socket_address}"
                    )
                if ttl < self.RedisClusterRequestTTL / 2:
                    time.sleep(0.05)

                self._emit_after_command_execution_event(
                    command_name=command,
                    duration_seconds=time.monotonic() - start_time,
                    connection=connection,
                    error=e,
                )
                self._emit_on_error_event(
                    error=e,
                    connection=connection,
                )
            except AskError as e:
                if is_debug_log_enabled():
                    socket_address = self._extracts_socket_address(connection)
                    args_log_str = truncate_text(" ".join(map(safe_str, args)))
                    logger.debug(
                        f"ASK error received for command {args_log_str}, on node {target_node.name}, "
                        f"and connection: {connection} using local socket address: {socket_address}, error: {e}"
                    )
                redirect_addr = get_node_name(host=e.host, port=e.port)
                asking = True

                self._emit_after_command_execution_event(
                    command_name=command,
                    duration_seconds=time.monotonic() - start_time,
                    connection=connection,
                    error=e,
                )
                self._emit_on_error_event(
                    error=e,
                    connection=connection,
                )
            except (ClusterDownError, SlotNotCoveredError) as e:
                # ClusterDownError can occur during a failover and to get
                # self-healed, we will try to reinitialize the cluster layout
                # and retry executing the command

                # SlotNotCoveredError can occur when the cluster is not fully
                # initialized or can be temporary issue.
                # We will try to reinitialize the cluster topology
                # and retry executing the command

                time.sleep(0.25)
                self.nodes_manager.initialize()

                e.connection = connection
                raise
            except ResponseError as e:
                e.connection = connection
                self._emit_after_command_execution_event(
                    command_name=command,
                    duration_seconds=time.monotonic() - start_time,
                    connection=connection,
                    error=e,
                )
                raise
            except Exception as e:
                if connection:
                    connection.disconnect()

                e.connection = connection
                raise e
            finally:
                if connection is not None:
                    redis_node.connection_pool.release(connection)

        e = ClusterError("TTL exhausted.")
        e.connection = connection
        raise e

    def _emit_after_command_execution_event(
        self,
        command_name: str,
        duration_seconds: float,
        connection: Connection,
        error=None,
    ):
        """
        Records operation duration metric directly.
        """
        record_operation_duration(
            command_name=command_name,
            duration_seconds=duration_seconds,
            server_address=connection.host,
            server_port=connection.port,
            db_namespace=str(connection.db),
            error=error,
        )

    def _emit_on_error_event(
        self,
        error: Exception,
        connection: Connection,
        is_internal: bool = True,
        retry_attempts: Optional[int] = None,
    ):
        """
        Records error count metric directly.
        """
        record_error_count(
            server_address=connection.host,
            server_port=connection.port,
            network_peer_address=connection.host,
            network_peer_port=connection.port,
            error_type=error,
            retry_attempts=retry_attempts if retry_attempts is not None else 0,
            is_internal=is_internal,
        )

    def _extracts_socket_address(
        self, connection: Optional[Connection]
    ) -> Optional[int]:
        if connection is None:
            return None
        try:
            socket_address = (
                connection._sock.getsockname() if connection._sock else None
            )
            socket_address = socket_address[1] if socket_address else None
        except (AttributeError, OSError):
            pass
        return socket_address

    def close(self) -> None:
        try:
            with self._lock:
                if self.nodes_manager:
                    self.nodes_manager.close()
        except AttributeError:
            # RedisCluster's __init__ can fail before nodes_manager is set
            pass

    def _process_result(self, command, res, response_policy: ResponsePolicy, **kwargs):
        """
        Process the result of the executed command.
        The function would return a dict or a single value.

        :type command: str
        :type res: dict

        `res` should be in the following format:
            Dict<node_name, command_result>
        """
        if command in self.result_callbacks:
            res = self.result_callbacks[command](command, res, **kwargs)
        elif len(res) == 1:
            # When we execute the command on a single node, we can
            # remove the dictionary and return a single response
            res = list(res.values())[0]

        return self._policies_callback_mapping[response_policy](res)

    def load_external_module(self, funcname, func):
        """
        This function can be used to add externally defined redis modules,
        and their namespaces to the redis client.

        ``funcname`` - A string containing the name of the function to create
        ``func`` - The function, being added to this class.
        """
        setattr(self, funcname, func)

    def transaction(self, func, *watches, **kwargs):
        """
        Convenience method for executing the callable `func` as a transaction
        while watching all keys specified in `watches`. The 'func' callable
        should expect a single argument which is a Pipeline object.
        """
        shard_hint = kwargs.pop("shard_hint", None)
        value_from_callable = kwargs.pop("value_from_callable", False)
        watch_delay = kwargs.pop("watch_delay", None)
        with self.pipeline(True, shard_hint) as pipe:
            while True:
                try:
                    if watches:
                        pipe.watch(*watches)
                    func_value = func(pipe)
                    exec_value = pipe.execute()
                    return func_value if value_from_callable else exec_value
                except WatchError:
                    if watch_delay is not None and watch_delay > 0:
                        time.sleep(watch_delay)
                    continue


class ClusterNode:
    def __init__(self, host, port, server_type=None, redis_connection=None):
        if host == "localhost":
            host = socket.gethostbyname(host)

        self.host = host
        self.port = port
        self.name = get_node_name(host, port)
        self.server_type = server_type
        self.redis_connection = redis_connection

    def __repr__(self):
        return (
            f"[host={self.host},"
            f"port={self.port},"
            f"name={self.name},"
            f"server_type={self.server_type},"
            f"redis_connection={self.redis_connection}]"
        )

    def __eq__(self, obj):
        return isinstance(obj, ClusterNode) and obj.name == self.name

    def __hash__(self):
        return hash(self.name)


class LoadBalancingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    ROUND_ROBIN_REPLICAS = "round_robin_replicas"
    RANDOM_REPLICA = "random_replica"


class LoadBalancer:
    """
    Round-Robin Load Balancing
    """

    def __init__(self, start_index: int = 0) -> None:
        self.primary_to_idx: dict[str, int] = {}
        self.start_index: int = start_index
        self._lock: threading.Lock = threading.Lock()

    def get_server_index(
        self,
        primary: str,
        list_size: int,
        load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
    ) -> int:
        if load_balancing_strategy == LoadBalancingStrategy.RANDOM_REPLICA:
            return self._get_random_replica_index(list_size)
        else:
            return self._get_round_robin_index(
                primary,
                list_size,
                load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN_REPLICAS,
            )

    def reset(self) -> None:
        with self._lock:
            self.primary_to_idx.clear()

    def _get_random_replica_index(self, list_size: int) -> int:
        return random.randint(1, list_size - 1)

    def _get_round_robin_index(
        self, primary: str, list_size: int, replicas_only: bool
    ) -> int:
        with self._lock:
            server_index = self.primary_to_idx.setdefault(primary, self.start_index)
            if replicas_only and server_index == 0:
                # skip the primary node index
                server_index = 1
            # Update the index for the next round
            self.primary_to_idx[primary] = (server_index + 1) % list_size
            return server_index


class NodesManager:
    def __init__(
        self,
        startup_nodes: list[ClusterNode],
        from_url=False,
        require_full_coverage=False,
        lock: Optional[threading.RLock] = None,
        dynamic_startup_nodes=True,
        connection_pool_class=ConnectionPool,
        address_remap: Optional[Callable[[Tuple[str, int]], Tuple[str, int]]] = None,
        cache: Optional[CacheInterface] = None,
        cache_config: Optional[CacheConfig] = None,
        cache_factory: Optional[CacheFactoryInterface] = None,
        event_dispatcher: Optional[EventDispatcher] = None,
        maint_notifications_config: Optional[MaintNotificationsConfig] = None,
        **kwargs,
    ):
        self.nodes_cache: dict[str, ClusterNode] = {}
        self.slots_cache: dict[int, list[ClusterNode]] = {}
        self.startup_nodes: dict[str, ClusterNode] = {n.name: n for n in startup_nodes}
        self.default_node: Optional[ClusterNode] = None
        self._epoch: int = 0
        self.from_url = from_url
        self._require_full_coverage = require_full_coverage
        self._dynamic_startup_nodes = dynamic_startup_nodes
        self.connection_pool_class = connection_pool_class
        self.address_remap = address_remap
        self._cache: Optional[CacheInterface] = None
        if cache:
            self._cache = cache
        elif cache_factory is not None:
            self._cache = cache_factory.get_cache()
        elif cache_config is not None:
            self._cache = CacheFactory(cache_config).get_cache()
        self.connection_kwargs = kwargs
        self.read_load_balancer = LoadBalancer()

        # nodes_cache / slots_cache / startup_nodes / default_node are protected by _lock
        if lock is None:
            self._lock = threading.RLock()
        else:
            self._lock = lock

        # initialize holds _initialization_lock to dedup multiple calls to reinitialize;
        # note that if we hold both _lock and _initialization_lock, we _must_ acquire
        # _initialization_lock first (ie: to have a consistent order) to avoid deadlock.
        self._initialization_lock: threading.RLock = threading.RLock()

        if event_dispatcher is None:
            self._event_dispatcher = EventDispatcher()
        else:
            self._event_dispatcher = event_dispatcher
        self._credential_provider = self.connection_kwargs.get(
            "credential_provider", None
        )
        self.maint_notifications_config = maint_notifications_config

        self.initialize()

    def get_node(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        node_name: Optional[str] = None,
    ) -> Optional[ClusterNode]:
        """
        Get the requested node from the cluster's nodes.
        nodes.
        :return: ClusterNode if the node exists, else None
        """
        if host and port:
            # the user passed host and port
            if host == "localhost":
                host = socket.gethostbyname(host)
            with self._lock:
                return self.nodes_cache.get(get_node_name(host=host, port=port))
        elif node_name:
            with self._lock:
                return self.nodes_cache.get(node_name)
        else:
            return None

    def move_slot(self, e: Union[AskError, MovedError]):
        """
        Update the slot's node with the redirected one
        """
        with self._lock:
            redirected_node = self.get_node(host=e.host, port=e.port)
            if redirected_node is not None:
                # The node already exists
                if redirected_node.server_type is not PRIMARY:
                    # Update the node's server type
                    redirected_node.server_type = PRIMARY
            else:
                # This is a new node, we will add it to the nodes cache
                redirected_node = ClusterNode(e.host, e.port, PRIMARY)
                self.nodes_cache[redirected_node.name] = redirected_node

            slot_nodes = self.slots_cache[e.slot_id]
            if redirected_node not in slot_nodes:
                # The new slot owner is a new server, or a server from a different
                # shard. We need to remove all current nodes from the slot's list
                # (including replications) and add just the new node.
                self.slots_cache[e.slot_id] = [redirected_node]
            elif redirected_node is not slot_nodes[0]:
                # The MOVED error resulted from a failover, and the new slot owner
                # had previously been a replica.
                old_primary = slot_nodes[0]
                # Update the old primary to be a replica and add it to the end of
                # the slot's node list
                old_primary.server_type = REPLICA
                slot_nodes.append(old_primary)
                # Remove the old replica, which is now a primary, from the slot's
                # node list
                slot_nodes.remove(redirected_node)
                # Override the old primary with the new one
                slot_nodes[0] = redirected_node
                if self.default_node == old_primary:
                    # Update the default node with the new primary
                    self.default_node = redirected_node
            # else: circular MOVED to current primary -> no-op

    @deprecated_args(
        args_to_warn=["server_type"],
        reason=(
            "In case you need select some load balancing strategy "
            "that will use replicas, please set it through 'load_balancing_strategy'"
        ),
        version="5.3.0",
    )
    def get_node_from_slot(
        self,
        slot: int,
        read_from_replicas: bool = False,
        load_balancing_strategy: Optional[LoadBalancingStrategy] = None,
        server_type: Optional[Literal["primary", "replica"]] = None,
    ) -> ClusterNode:
        """
        Gets a node that servers this hash slot
        """

        if read_from_replicas is True and load_balancing_strategy is None:
            load_balancing_strategy = LoadBalancingStrategy.ROUND_ROBIN

        with self._lock:
            if self.slots_cache.get(slot) is None or len(self.slots_cache[slot]) == 0:
                raise SlotNotCoveredError(
                    f'Slot "{slot}" not covered by the cluster. '
                    + f'"require_full_coverage={self._require_full_coverage}"'
                )

            if len(self.slots_cache[slot]) > 1 and load_balancing_strategy:
                # get the server index using the strategy defined in load_balancing_strategy
                primary_name = self.slots_cache[slot][0].name
                node_idx = self.read_load_balancer.get_server_index(
                    primary_name, len(self.slots_cache[slot]), load_balancing_strategy
                )
            elif (
                server_type is None
                or server_type == PRIMARY
                or len(self.slots_cache[slot]) == 1
            ):
                # return a primary
                node_idx = 0
            else:
                # return a replica
                # randomly choose one of the replicas
                node_idx = random.randint(1, len(self.slots_cache[slot]) - 1)

            return self.slots_cache[slot][node_idx]

    def get_nodes_by_server_type(self, server_type: Literal["primary", "replica"]):
        """
        Get all nodes with the specified server type
        :param server_type: 'primary' or 'replica'
        :return: list of ClusterNode
        """
        with self._lock:
            return [
                node
                for node in self.nodes_cache.values()
                if node.server_type == server_type
            ]

    @deprecated_function(
        reason="This method is not used anymore internally. The startup nodes are populated automatically.",
        version="7.0.2",
    )
    def populate_startup_nodes(self, nodes):
        """
        Populate all startup nodes and filters out any duplicates
        """
        with self._lock:
            for n in nodes:
                self.startup_nodes[n.name] = n

    def move_node_to_end_of_cached_nodes(self, node_name: str) -> None:
        """
        Move a failing node to the end of startup_nodes and nodes_cache so it's
        tried last during reinitialization and when selecting the default node.
        If the node is not in the respective list, nothing is done.
        """
        # Move in startup_nodes
        if node_name in self.startup_nodes and len(self.startup_nodes) > 1:
            node = self.startup_nodes.pop(node_name)
            self.startup_nodes[node_name] = node  # Re-insert at end

        # Move in nodes_cache - this affects get_nodes_by_server_type ordering
        # which is used to select the default_node during initialize()
        if node_name in self.nodes_cache and len(self.nodes_cache) > 1:
            node = self.nodes_cache.pop(node_name)
            self.nodes_cache[node_name] = node  # Re-insert at end

    def check_slots_coverage(self, slots_cache):
        # Validate if all slots are covered or if we should try next
        # startup node
        for i in range(0, REDIS_CLUSTER_HASH_SLOTS):
            if i not in slots_cache:
                return False
        return True

    def create_redis_connections(self, nodes):
        """
        This function will create a redis connection to all nodes in :nodes:
        """
        connection_pools = []
        for node in nodes:
            if node.redis_connection is None:
                node.redis_connection = self.create_redis_node(
                    host=node.host,
                    port=node.port,
                    maint_notifications_config=self.maint_notifications_config,
                    **self.connection_kwargs,
                )
                connection_pools.append(node.redis_connection.connection_pool)

        self._event_dispatcher.dispatch(
            AfterPooledConnectionsInstantiationEvent(
                connection_pools, ClientType.SYNC, self._credential_provider
            )
        )

    def create_redis_node(
        self,
        host,
        port,
        **kwargs,
    ):
        # We are configuring the connection pool not to retry
        # connections on lower level clients to avoid retrying
        # connections to nodes that are not reachable
        # and to avoid blocking the connection pool.
        # The only error that will have some handling in the lower
        # level clients is ConnectionError which will trigger disconnection
        # of the socket.
        # The retries will be handled on cluster client level
        # where we will have proper handling of the cluster topology
        node_retry_config = Retry(
            backoff=NoBackoff(), retries=0, supported_errors=(ConnectionError,)
        )

        if self.from_url:
            # Create a redis node with a custom connection pool
            kwargs.update({"host": host})
            kwargs.update({"port": port})
            kwargs.update({"cache": self._cache})
            kwargs.update({"retry": node_retry_config})
            r = Redis(connection_pool=self.connection_pool_class(**kwargs))
        else:
            r = Redis(
                host=host,
                port=port,
                cache=self._cache,
                retry=node_retry_config,
                **kwargs,
            )
        return r

    def _get_or_create_cluster_node(self, host, port, role, tmp_nodes_cache):
        node_name = get_node_name(host, port)
        # check if we already have this node in the tmp_nodes_cache
        target_node = tmp_nodes_cache.get(node_name)
        if target_node is None:
            # before creating a new cluster node, check if the cluster node already
            # exists in the current nodes cache and has a valid connection so we can
            # reuse it
            redis_connection: Optional[Redis] = None
            with self._lock:
                previous_node = self.nodes_cache.get(node_name)
                if previous_node:
                    redis_connection = previous_node.redis_connection
            # don't update the old ClusterNode, so we don't update its role
            # outside of the lock
            target_node = ClusterNode(host, port, role, redis_connection)
            # add this node to the nodes cache
            tmp_nodes_cache[target_node.name] = target_node

        return target_node

    def _get_epoch(self) -> int:
        """
        Get the current epoch value. This method exists primarily to allow
        tests to mock the epoch fetch and control race condition timing.
        """
        with self._lock:
            return self._epoch

    def initialize(
        self,
        additional_startup_nodes_info: Optional[List[Tuple[str, int]]] = None,
        disconnect_startup_nodes_pools: bool = True,
    ):
        """
        Initializes the nodes cache, slots cache and redis connections.
        :startup_nodes:
            Responsible for discovering other nodes in the cluster
        :disconnect_startup_nodes_pools:
            Whether to disconnect the connection pool of the startup nodes
            after the initialization is complete. This is useful when the
            startup nodes are not part of the cluster and we want to avoid
            keeping the connection open.
        :additional_startup_nodes_info:
            Additional nodes to add temporarily to the startup nodes.
            The additional nodes will be used just in the process of extraction of the slots
            and nodes information from the cluster.
            This is useful when we want to add new nodes to the cluster
            and initialize the client
            with them.
            The format of the list is a list of tuples, where each tuple contains
            the host and port of the node.
        """
        self.reset()
        tmp_nodes_cache = {}
        tmp_slots = {}
        disagreements = []
        startup_nodes_reachable = False
        fully_covered = False
        kwargs = self.connection_kwargs
        exception = None
        epoch = self._get_epoch()
        if additional_startup_nodes_info is None:
            additional_startup_nodes_info = []

        with self._initialization_lock:
            with self._lock:
                if epoch != self._epoch:
                    # another thread has already re-initialized the nodes; don't
                    # bother running again
                    return

            with self._lock:
                startup_nodes = tuple(self.startup_nodes.values())

            additional_startup_nodes = [
                ClusterNode(host, port) for host, port in additional_startup_nodes_info
            ]
            if is_debug_log_enabled():
                logger.debug(
                    f"Topology refresh: using additional nodes: {[node.name for node in additional_startup_nodes]}; "
                    f"and startup nodes: {[node.name for node in startup_nodes]}"
                )

            for startup_node in (*startup_nodes, *additional_startup_nodes):
                try:
                    if startup_node.redis_connection:
                        r = startup_node.redis_connection

                    else:
                        # Create a new Redis connection
                        if is_debug_log_enabled():
                            socket_timeout = kwargs.get("socket_timeout", "not set")
                            socket_connect_timeout = kwargs.get(
                                "socket_connect_timeout", "not set"
                            )
                            maint_enabled = (
                                self.maint_notifications_config.enabled
                                if self.maint_notifications_config
                                else False
                            )
                            logger.debug(
                                "Topology refresh: Creating new Redis connection to "
                                f"{startup_node.host}:{startup_node.port}; "
                                f"with socket_timeout: {socket_timeout}, and "
                                f"socket_connect_timeout: {socket_connect_timeout}, "
                                "and maint_notifications enabled: "
                                f"{maint_enabled}"
                            )
                        r = self.create_redis_node(
                            startup_node.host,
                            startup_node.port,
                            maint_notifications_config=self.maint_notifications_config,
                            **kwargs,
                        )
                        if startup_node in self.startup_nodes.values():
                            self.startup_nodes[startup_node.name].redis_connection = r
                        else:
                            startup_node.redis_connection = r
                    try:
                        # Make sure cluster mode is enabled on this node
                        cluster_slots = str_if_bytes(r.execute_command("CLUSTER SLOTS"))
                        if disconnect_startup_nodes_pools:
                            with r.connection_pool._lock:
                                # take care to clear connections before we move on
                                # mark all active connections for reconnect - they will be
                                # reconnected on next use, but will allow current in flight commands to complete first
                                r.connection_pool.update_active_connections_for_reconnect()
                                # Needed to clear READONLY state when it is no longer applicable
                                r.connection_pool.disconnect_free_connections()
                    except ResponseError:
                        raise RedisClusterException(
                            "Cluster mode is not enabled on this node"
                        )
                    startup_nodes_reachable = True
                except Exception as e:
                    # Try the next startup node.
                    # The exception is saved and raised only if we have no more nodes.
                    exception = e
                    continue

                # CLUSTER SLOTS command results in the following output:
                # [[slot_section[from_slot,to_slot,master,replica1,...,replicaN]]]
                # where each node contains the following list: [IP, port, node_id]
                # Therefore, cluster_slots[0][2][0] will be the IP address of the
                # primary node of the first slot section.
                # If there's only one server in the cluster, its ``host`` is ''
                # Fix it to the host in startup_nodes
                if (
                    len(cluster_slots) == 1
                    and len(cluster_slots[0][2][0]) == 0
                    and len(self.startup_nodes) == 1
                ):
                    cluster_slots[0][2][0] = startup_node.host

                for slot in cluster_slots:
                    primary_node = slot[2]
                    host = str_if_bytes(primary_node[0])
                    if host == "":
                        host = startup_node.host
                    port = int(primary_node[1])
                    host, port = self.remap_host_port(host, port)

                    nodes_for_slot = []

                    target_node = self._get_or_create_cluster_node(
                        host, port, PRIMARY, tmp_nodes_cache
                    )
                    nodes_for_slot.append(target_node)

                    replica_nodes = slot[3:]
                    for replica_node in replica_nodes:
                        host = str_if_bytes(replica_node[0])
                        port = int(replica_node[1])
                        host, port = self.remap_host_port(host, port)
                        target_replica_node = self._get_or_create_cluster_node(
                            host, port, REPLICA, tmp_nodes_cache
                        )
                        nodes_for_slot.append(target_replica_node)

                    for i in range(int(slot[0]), int(slot[1]) + 1):
                        if i not in tmp_slots:
                            tmp_slots[i] = nodes_for_slot
                        else:
                            # Validate that 2 nodes want to use the same slot cache
                            # setup
                            tmp_slot = tmp_slots[i][0]
                            if tmp_slot.name != target_node.name:
                                disagreements.append(
                                    f"{tmp_slot.name} vs {target_node.name} on slot: {i}"
                                )

                                if len(disagreements) > 5:
                                    raise RedisClusterException(
                                        f"startup_nodes could not agree on a valid "
                                        f"slots cache: {', '.join(disagreements)}"
                                    )

                fully_covered = self.check_slots_coverage(tmp_slots)
                if fully_covered:
                    # Don't need to continue to the next startup node if all
                    # slots are covered
                    break

            if not startup_nodes_reachable:
                raise RedisClusterException(
                    f"Redis Cluster cannot be connected. Please provide at least "
                    f"one reachable node: {str(exception)}"
                ) from exception

            # Create Redis connections to all nodes
            self.create_redis_connections(list(tmp_nodes_cache.values()))

            # Check if the slots are not fully covered
            if not fully_covered and self._require_full_coverage:
                # Despite the requirement that the slots be covered, there
                # isn't a full coverage
                raise RedisClusterException(
                    f"All slots are not covered after query all startup_nodes. "
                    f"{len(tmp_slots)} of {REDIS_CLUSTER_HASH_SLOTS} "
                    f"covered..."
                )

            # Set the tmp variables to the real variables
            with self._lock:
                self.nodes_cache = tmp_nodes_cache
                self.slots_cache = tmp_slots
                # Set the default node
                self.default_node = self.get_nodes_by_server_type(PRIMARY)[0]
                if self._dynamic_startup_nodes:
                    # Populate the startup nodes with all discovered nodes
                    self.startup_nodes = tmp_nodes_cache
                # Increment the epoch to signal that initialization has completed
                self._epoch += 1

    def close(self) -> None:
        with self._lock:
            self.default_node = None
            nodes = tuple(self.nodes_cache.values())
        for node in nodes:
            if node.redis_connection:
                node.redis_connection.close()

    def reset(self):
        try:
            self.read_load_balancer.reset()
        except TypeError:
            # The read_load_balancer is None, do nothing
            pass

    def remap_host_port(self, host: str, port: int) -> Tuple[str, int]:
        """
        Remap the host and port returned from the cluster to a different
        internal value.  Useful if the client is not connecting directly
        to the cluster.
        """
        if self.address_remap:
            return self.address_remap((host, port))
        return host, port

    def find_connection_owner(self, connection: Connection) -> Optional[ClusterNode]:
        node_name = get_node_name(connection.host, connection.port)
        with self._lock:
            for node in tuple(self.nodes_cache.values()):
                if node.redis_connection:
                    conn_args = node.redis_connection.connection_pool.connection_kwargs
                    if node_name == get_node_name(
                        conn_args.get("host"), conn_args.get("port")
                    ):
                        return node
        return None


class ClusterPubSub(PubSub):
    """
    Wrapper for PubSub class.

    IMPORTANT: before using ClusterPubSub, read about the known limitations
    with pubsub in Cluster mode and learn how to workaround them:
    https://redis-py-cluster.readthedocs.io/en/stable/pubsub.html
    """

    def __init__(
        self,
        redis_cluster,
        node=None,
        host=None,
        port=None,
        push_handler_func=None,
        event_dispatcher: Optional["EventDispatcher"] = None,
        **kwargs,
    ):
        """
        When a pubsub instance is created without specifying a node, a single
        node will be transparently chosen for the pubsub connection on the
        first command execution. The node will be determined by:
         1. Hashing the channel name in the request to find its keyslot
         2. Selecting a node that handles the keyslot: If read_from_replicas is
            set to true or load_balancing_strategy is set, a replica can be selected.

        :type redis_cluster: RedisCluster
        :type node: ClusterNode
        :type host: str
        :type port: int
        """
        self.node = None
        self.set_pubsub_node(redis_cluster, node, host, port)
        connection_pool = (
            None
            if self.node is None
            else redis_cluster.get_redis_connection(self.node).connection_pool
        )
        self.cluster = redis_cluster
        self.node_pubsub_mapping = {}
        self._pubsubs_generator = self._pubsubs_generator()
        if event_dispatcher is None:
            self._event_dispatcher = EventDispatcher()
        else:
            self._event_dispatcher = event_dispatcher
        super().__init__(
            connection_pool=connection_pool,
            encoder=redis_cluster.encoder,
            push_handler_func=push_handler_func,
            event_dispatcher=self._event_dispatcher,
            **kwargs,
        )

    def set_pubsub_node(self, cluster, node=None, host=None, port=None):
        """
        The pubsub node will be set according to the passed node, host and port
        When none of the node, host, or port are specified - the node is set
        to None and will be determined by the keyslot of the channel in the
        first command to be executed.
        RedisClusterException will be thrown if the passed node does not exist
        in the cluster.
        If host is passed without port, or vice versa, a DataError will be
        thrown.
        :type cluster: RedisCluster
        :type node: ClusterNode
        :type host: str
        :type port: int
        """
        if node is not None:
            # node is passed by the user
            self._raise_on_invalid_node(cluster, node, node.host, node.port)
            pubsub_node = node
        elif host is not None and port is not None:
            # host and port passed by the user
            node = cluster.get_node(host=host, port=port)
            self._raise_on_invalid_node(cluster, node, host, port)
            pubsub_node = node
        elif any([host, port]) is True:
            # only 'host' or 'port' passed
            raise DataError("Passing a host requires passing a port, and vice versa")
        else:
            # nothing passed by the user. set node to None
            pubsub_node = None

        self.node = pubsub_node

    def get_pubsub_node(self):
        """
        Get the node that is being used as the pubsub connection
        """
        return self.node

    def _raise_on_invalid_node(self, redis_cluster, node, host, port):
        """
        Raise a RedisClusterException if the node is None or doesn't exist in
        the cluster.
        """
        if node is None or redis_cluster.get_node(node_name=node.name) is None:
            raise RedisClusterException(
                f"Node {host}:{port} doesn't exist in the cluster"
            )

    def execute_command(self, *args):
        """
        Execute a subscribe/unsubscribe command.

        Taken code from redis-py and tweak to make it work within a cluster.
        """
        # NOTE: don't parse the response in this function -- it could pull a
        # legitimate message off the stack if the connection is already
        # subscribed to one or more channels

        if self.connection is None:
            if self.connection_pool is None:
                if len(args) > 1:
                    # Hash the first channel and get one of the nodes holding
                    # this slot
                    channel = args[1]
                    slot = self.cluster.keyslot(channel)
                    node = self.cluster.nodes_manager.get_node_from_slot(
                        slot,
                        self.cluster.read_from_replicas,
                        self.cluster.load_balancing_strategy,
                    )
                else:
                    # Get a random node
                    node = self.cluster.get_random_node()
                self.node = node
                redis_connection = self.cluster.get_redis_connection(node)
                self.connection_pool = redis_connection.connection_pool
            self.connection = self.connection_pool.get_connection()
            # register a callback that re-subscribes to any channels we
            # were listening to when we were disconnected
            self.connection.register_connect_callback(self.on_connect)
            if self.push_handler_func is not None:
                self.connection._parser.set_pubsub_push_handler(self.push_handler_func)
            self._event_dispatcher.dispatch(
                AfterPubSubConnectionInstantiationEvent(
                    self.connection, self.connection_pool, ClientType.SYNC, self._lock
                )
            )
        connection = self.connection
        self._execute(connection, connection.send_command, *args)

    def _get_node_pubsub(self, node):
        try:
            return self.node_pubsub_mapping[node.name]
        except KeyError:
            pubsub = node.redis_connection.pubsub(
                push_handler_func=self.push_handler_func
            )
            self.node_pubsub_mapping[node.name] = pubsub
            return pubsub

    def _sharded_message_generator(self):
        for _ in range(len(self.node_pubsub_mapping)):
            pubsub = next(self._pubsubs_generator)
            message = pubsub.get_message()
            if message is not None:
                return message
        return None

    def _pubsubs_generator(self):
        while True:
            current_nodes = list(self.node_pubsub_mapping.values())
            yield from current_nodes

    def get_sharded_message(
        self, ignore_subscribe_messages=False, timeout=0.0, target_node=None
    ):
        if target_node:
            message = self.node_pubsub_mapping[target_node.name].get_message(
                ignore_subscribe_messages=ignore_subscribe_messages, timeout=timeout
            )
        else:
            message = self._sharded_message_generator()
        if message is None:
            return None
        elif str_if_bytes(message["type"]) == "sunsubscribe":
            if message["channel"] in self.pending_unsubscribe_shard_channels:
                self.pending_unsubscribe_shard_channels.remove(message["channel"])
                self.shard_channels.pop(message["channel"], None)
                node = self.cluster.get_node_from_key(message["channel"])
                if self.node_pubsub_mapping[node.name].subscribed is False:
                    self.node_pubsub_mapping.pop(node.name)
        if not self.channels and not self.patterns and not self.shard_channels:
            # There are no subscriptions anymore, set subscribed_event flag
            # to false
            self.subscribed_event.clear()
        if self.ignore_subscribe_messages or ignore_subscribe_messages:
            return None
        return message

    def ssubscribe(self, *args, **kwargs):
        if args:
            args = list_or_args(args[0], args[1:])
        s_channels = dict.fromkeys(args)
        s_channels.update(kwargs)
        for s_channel, handler in s_channels.items():
            node = self.cluster.get_node_from_key(s_channel)
            pubsub = self._get_node_pubsub(node)
            if handler:
                pubsub.ssubscribe(**{s_channel: handler})
            else:
                pubsub.ssubscribe(s_channel)
            self.shard_channels.update(pubsub.shard_channels)
            self.pending_unsubscribe_shard_channels.difference_update(
                self._normalize_keys({s_channel: None})
            )
            if pubsub.subscribed and not self.subscribed:
                self.subscribed_event.set()
                self.health_check_response_counter = 0

    def sunsubscribe(self, *args):
        if args:
            args = list_or_args(args[0], args[1:])
        else:
            args = self.shard_channels

        for s_channel in args:
            node = self.cluster.get_node_from_key(s_channel)
            p = self._get_node_pubsub(node)
            p.sunsubscribe(s_channel)
            self.pending_unsubscribe_shard_channels.update(
                p.pending_unsubscribe_shard_channels
            )

    def get_redis_connection(self):
        """
        Get the Redis connection of the pubsub connected node.
        """
        if self.node is not None:
            return self.node.redis_connection

    def disconnect(self):
        """
        Disconnect the pubsub connection.
        """
        if self.connection:
            self.connection.disconnect()
        for pubsub in self.node_pubsub_mapping.values():
            pubsub.connection.disconnect()


class ClusterPipeline(RedisCluster):
    """
    Support for Redis pipeline
    in cluster mode
    """

    ERRORS_ALLOW_RETRY = (
        ConnectionError,
        TimeoutError,
        MovedError,
        AskError,
        TryAgainError,
    )

    NO_SLOTS_COMMANDS = {"UNWATCH"}
    IMMEDIATE_EXECUTE_COMMANDS = {"WATCH", "UNWATCH"}
    UNWATCH_COMMANDS = {"DISCARD", "EXEC", "UNWATCH"}

    @deprecated_args(
        args_to_warn=[
            "cluster_error_retry_attempts",
        ],
        reason="Please configure the 'retry' object instead",
        version="6.0.0",
    )
    def __init__(
        self,
        nodes_manager: "NodesManager",
        commands_parser: "CommandsParser",
        result_callbacks: Optional[Dict[str, Callable]] = None,
        cluster_response_callbacks: Optional[Dict[str, Callable]] = None,
        startup_nodes: Optional[List["ClusterNode"]] = None,
        read_from_replicas: bool = False,
        load_balancing_strategy: Optional[LoadBalancingStrategy] = None,
        cluster_error_retry_attempts: int = 3,
        reinitialize_steps: int = 5,
        retry: Optional[Retry] = None,
        lock=None,
        transaction=False,
        policy_resolver: PolicyResolver = StaticPolicyResolver(),
        event_dispatcher: Optional["EventDispatcher"] = None,
        **kwargs,
    ):
        """ """
        self.command_stack = []
        self.nodes_manager = nodes_manager
        self.commands_parser = commands_parser
        self.refresh_table_asap = False
        self.result_callbacks = (
            result_callbacks or self.__class__.RESULT_CALLBACKS.copy()
        )
        self.startup_nodes = startup_nodes if startup_nodes else []
        self.read_from_replicas = read_from_replicas
        self.load_balancing_strategy = load_balancing_strategy
        self.command_flags = self.__class__.COMMAND_FLAGS.copy()
        self.cluster_response_callbacks = cluster_response_callbacks
        self.reinitialize_counter = 0
        self.reinitialize_steps = reinitialize_steps
        if retry is not None:
            self.retry = retry
        else:
            self.retry = Retry(
                backoff=ExponentialWithJitterBackoff(base=1, cap=10),
                retries=cluster_error_retry_attempts,
            )

        self.encoder = Encoder(
            kwargs.get("encoding", "utf-8"),
            kwargs.get("encoding_errors", "strict"),
            kwargs.get("decode_responses", False),
        )
        if lock is None:
            lock = threading.RLock()
        self._lock = lock
        self.parent_execute_command = super().execute_command
        self._execution_strategy: ExecutionStrategy = (
            PipelineStrategy(self) if not transaction else TransactionStrategy(self)
        )

        # For backward compatibility, mapping from existing policies to new one
        self._command_flags_mapping: dict[str, Union[RequestPolicy, ResponsePolicy]] = {
            self.__class__.RANDOM: RequestPolicy.DEFAULT_KEYLESS,
            self.__class__.PRIMARIES: RequestPolicy.ALL_SHARDS,
            self.__class__.ALL_NODES: RequestPolicy.ALL_NODES,
            self.__class__.REPLICAS: RequestPolicy.ALL_REPLICAS,
            self.__class__.DEFAULT_NODE: RequestPolicy.DEFAULT_NODE,
            SLOT_ID: RequestPolicy.DEFAULT_KEYED,
        }

        self._policies_callback_mapping: dict[
            Union[RequestPolicy, ResponsePolicy], Callable
        ] = {
            RequestPolicy.DEFAULT_KEYLESS: lambda command_name: [
                self.get_random_primary_or_all_nodes(command_name)
            ],
            RequestPolicy.DEFAULT_KEYED: lambda command,
            *args: self.get_nodes_from_slot(command, *args),
            RequestPolicy.DEFAULT_NODE: lambda: [self.get_default_node()],
            RequestPolicy.ALL_SHARDS: self.get_primaries,
            RequestPolicy.ALL_NODES: self.get_nodes,
            RequestPolicy.ALL_REPLICAS: self.get_replicas,
            RequestPolicy.MULTI_SHARD: lambda *args,
            **kwargs: self._split_multi_shard_command(*args, **kwargs),
            RequestPolicy.SPECIAL: self.get_special_nodes,
            ResponsePolicy.DEFAULT_KEYLESS: lambda res: res,
            ResponsePolicy.DEFAULT_KEYED: lambda res: res,
        }

        self._policy_resolver = policy_resolver

        if event_dispatcher is None:
            self._event_dispatcher = EventDispatcher()
        else:
            self._event_dispatcher = event_dispatcher

    def __repr__(self):
        """ """
        return f"{type(self).__name__}"

    def __enter__(self):
        """ """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """ """
        self.reset()

    def __del__(self):
        try:
            self.reset()
        except Exception:
            pass

    def __len__(self):
        """ """
        return len(self._execution_strategy.command_queue)

    def __bool__(self):
        "Pipeline instances should  always evaluate to True on Python 3+"
        return True

    def execute_command(self, *args, **kwargs):
        """
        Wrapper function for pipeline_execute_command
        """
        return self._execution_strategy.execute_command(*args, **kwargs)

    def pipeline_execute_command(self, *args, **options):
        """
        Stage a command to be executed when execute() is next called

        Returns the current Pipeline object back so commands can be
        chained together, such as:

        pipe = pipe.set('foo', 'bar').incr('baz').decr('bang')

        At some other point, you can then run: pipe.execute(),
        which will execute all commands queued in the pipe.
        """
        return self._execution_strategy.execute_command(*args, **options)

    def annotate_exception(self, exception, number, command):
        """
        Provides extra context to the exception prior to it being handled
        """
        self._execution_strategy.annotate_exception(exception, number, command)

    def execute(self, raise_on_error: bool = True) -> List[Any]:
        """
        Execute all the commands in the current pipeline
        """

        try:
            return self._execution_strategy.execute(raise_on_error)
        finally:
            self.reset()

    def reset(self):
        """
        Reset back to empty pipeline.
        """
        self._execution_strategy.reset()

    def send_cluster_commands(
        self, stack, raise_on_error=True, allow_redirections=True
    ):
        return self._execution_strategy.send_cluster_commands(
            stack, raise_on_error=raise_on_error, allow_redirections=allow_redirections
        )

    def exists(self, *keys):
        return self._execution_strategy.exists(*keys)

    def eval(self):
        """ """
        return self._execution_strategy.eval()

    def multi(self):
        """
        Start a transactional block of the pipeline after WATCH commands
        are issued. End the transactional block with `execute`.
        """
        self._execution_strategy.multi()

    def load_scripts(self):
        """ """
        self._execution_strategy.load_scripts()

    def discard(self):
        """ """
        self._execution_strategy.discard()

    def watch(self, *names):
        """Watches the values at keys ``names``"""
        self._execution_strategy.watch(*names)

    def unwatch(self):
        """Unwatches all previously specified keys"""
        self._execution_strategy.unwatch()

    def script_load_for_pipeline(self, *args, **kwargs):
        self._execution_strategy.script_load_for_pipeline(*args, **kwargs)

    def delete(self, *names):
        self._execution_strategy.delete(*names)

    def unlink(self, *names):
        self._execution_strategy.unlink(*names)


def block_pipeline_command(name: str) -> Callable[..., Any]:
    """
    Prints error because some pipelined commands should
    be blocked when running in cluster-mode
    """

    def inner(*args, **kwargs):
        raise RedisClusterException(
            f"ERROR: Calling pipelined function {name} is blocked "
            f"when running redis in cluster mode..."
        )

    return inner


# Blocked pipeline commands
PIPELINE_BLOCKED_COMMANDS = (
    "BGREWRITEAOF",
    "BGSAVE",
    "BITOP",
    "BRPOPLPUSH",
    "CLIENT GETNAME",
    "CLIENT KILL",
    "CLIENT LIST",
    "CLIENT SETNAME",
    "CLIENT",
    "CONFIG GET",
    "CONFIG RESETSTAT",
    "CONFIG REWRITE",
    "CONFIG SET",
    "CONFIG",
    "DBSIZE",
    "ECHO",
    "EVALSHA",
    "FLUSHALL",
    "FLUSHDB",
    "INFO",
    "KEYS",
    "LASTSAVE",
    "MGET",
    "MGET NONATOMIC",
    "MOVE",
    "MSET",
    "MSETEX",
    "MSET NONATOMIC",
    "MSETNX",
    "PFCOUNT",
    "PFMERGE",
    "PING",
    "PUBLISH",
    "RANDOMKEY",
    "READONLY",
    "READWRITE",
    "RENAME",
    "RENAMENX",
    "RPOPLPUSH",
    "SAVE",
    "SCAN",
    "SCRIPT EXISTS",
    "SCRIPT FLUSH",
    "SCRIPT KILL",
    "SCRIPT LOAD",
    "SCRIPT",
    "SDIFF",
    "SDIFFSTORE",
    "SENTINEL GET MASTER ADDR BY NAME",
    "SENTINEL MASTER",
    "SENTINEL MASTERS",
    "SENTINEL MONITOR",
    "SENTINEL REMOVE",
    "SENTINEL SENTINELS",
    "SENTINEL SET",
    "SENTINEL SLAVES",
    "SENTINEL",
    "SHUTDOWN",
    "SINTER",
    "SINTERSTORE",
    "SLAVEOF",
    "SLOWLOG GET",
    "SLOWLOG LEN",
    "SLOWLOG RESET",
    "SLOWLOG",
    "SMOVE",
    "SORT",
    "SUNION",
    "SUNIONSTORE",
    "TIME",
)
for command in PIPELINE_BLOCKED_COMMANDS:
    command = command.replace(" ", "_").lower()

    setattr(ClusterPipeline, command, block_pipeline_command(command))


class PipelineCommand:
    """ """

    def __init__(self, args, options=None, position=None):
        self.args = args
        if options is None:
            options = {}
        self.options = options
        self.position = position
        self.result = None
        self.node = None
        self.asking = False
        self.command_policies: Optional[CommandPolicies] = None


class NodeCommands:
    """ """

    def __init__(self, parse_response, connection_pool, connection):
        """ """
        self.parse_response = parse_response
        self.connection_pool = connection_pool
        self.connection = connection
        self.commands = []

    def append(self, c):
        """ """
        self.commands.append(c)

    def write(self):
        """
        Code borrowed from Redis so it can be fixed
        """
        connection = self.connection
        commands = self.commands

        # We are going to clobber the commands with the write, so go ahead
        # and ensure that nothing is sitting there from a previous run.
        for c in commands:
            c.result = None

        # build up all commands into a single request to increase network perf
        # send all the commands and catch connection and timeout errors.
        try:
            connection.send_packed_command(
                connection.pack_commands([c.args for c in commands])
            )
        except (ConnectionError, TimeoutError) as e:
            for c in commands:
                c.result = e

    def read(self):
        """ """
        connection = self.connection
        for c in self.commands:
            # if there is a result on this command,
            # it means we ran into an exception
            # like a connection error. Trying to parse
            # a response on a connection that
            # is no longer open will result in a
            # connection error raised by redis-py.
            # but redis-py doesn't check in parse_response
            # that the sock object is
            # still set and if you try to
            # read from a closed connection, it will
            # result in an AttributeError because
            # it will do a readline() call on None.
            # This can have all kinds of nasty side-effects.
            # Treating this case as a connection error
            # is fine because it will dump
            # the connection object back into the
            # pool and on the next write, it will
            # explicitly open the connection and all will be well.
            if c.result is None:
                try:
                    c.result = self.parse_response(connection, c.args[0], **c.options)
                except (ConnectionError, TimeoutError) as e:
                    for c in self.commands:
                        c.result = e
                    return
                except RedisError:
                    c.result = sys.exc_info()[1]


class ExecutionStrategy(ABC):
    @property
    @abstractmethod
    def command_queue(self):
        pass

    @abstractmethod
    def execute_command(self, *args, **kwargs):
        """
        Execution flow for current execution strategy.

        See: ClusterPipeline.execute_command()
        """
        pass

    @abstractmethod
    def annotate_exception(self, exception, number, command):
        """
        Annotate exception according to current execution strategy.

        See: ClusterPipeline.annotate_exception()
        """
        pass

    @abstractmethod
    def pipeline_execute_command(self, *args, **options):
        """
        Pipeline execution flow for current execution strategy.

        See: ClusterPipeline.pipeline_execute_command()
        """
        pass

    @abstractmethod
    def execute(self, raise_on_error: bool = True) -> List[Any]:
        """
        Executes current execution strategy.

        See: ClusterPipeline.execute()
        """
        pass

    @abstractmethod
    def send_cluster_commands(
        self, stack, raise_on_error=True, allow_redirections=True
    ):
        """
        Sends commands according to current execution strategy.

        See: ClusterPipeline.send_cluster_commands()
        """
        pass

    @abstractmethod
    def reset(self):
        """
        Resets current execution strategy.

        See: ClusterPipeline.reset()
        """
        pass

    @abstractmethod
    def exists(self, *keys):
        pass

    @abstractmethod
    def eval(self):
        pass

    @abstractmethod
    def multi(self):
        """
        Starts transactional context.

        See: ClusterPipeline.multi()
        """
        pass

    @abstractmethod
    def load_scripts(self):
        pass

    @abstractmethod
    def watch(self, *names):
        pass

    @abstractmethod
    def unwatch(self):
        """
        Unwatches all previously specified keys

        See: ClusterPipeline.unwatch()
        """
        pass

    @abstractmethod
    def script_load_for_pipeline(self, *args, **kwargs):
        pass

    @abstractmethod
    def delete(self, *names):
        """
        "Delete a key specified by ``names``"

        See: ClusterPipeline.delete()
        """
        pass

    @abstractmethod
    def unlink(self, *names):
        """
        "Unlink a key specified by ``names``"

        See: ClusterPipeline.unlink()
        """
        pass

    @abstractmethod
    def discard(self):
        pass


class AbstractStrategy(ExecutionStrategy):
    def __init__(
        self,
        pipe: ClusterPipeline,
    ):
        self._command_queue: List[PipelineCommand] = []
        self._pipe = pipe
        self._nodes_manager = self._pipe.nodes_manager

    @property
    def command_queue(self):
        return self._command_queue

    @command_queue.setter
    def command_queue(self, queue: List[PipelineCommand]):
        self._command_queue = queue

    @abstractmethod
    def execute_command(self, *args, **kwargs):
        pass

    def pipeline_execute_command(self, *args, **options):
        self._command_queue.append(
            PipelineCommand(args, options, len(self._command_queue))
        )
        return self._pipe

    @abstractmethod
    def execute(self, raise_on_error: bool = True) -> List[Any]:
        pass

    @abstractmethod
    def send_cluster_commands(
        self, stack, raise_on_error=True, allow_redirections=True
    ):
        pass

    @abstractmethod
    def reset(self):
        pass

    def exists(self, *keys):
        return self.execute_command("EXISTS", *keys)

    def eval(self):
        """ """
        raise RedisClusterException("method eval() is not implemented")

    def load_scripts(self):
        """ """
        raise RedisClusterException("method load_scripts() is not implemented")

    def script_load_for_pipeline(self, *args, **kwargs):
        """ """
        raise RedisClusterException(
            "method script_load_for_pipeline() is not implemented"
        )

    def annotate_exception(self, exception, number, command):
        """
        Provides extra context to the exception prior to it being handled
        """
        cmd = " ".join(map(safe_str, command))
        msg = (
            f"Command # {number} ({truncate_text(cmd)}) of pipeline "
            f"caused error: {exception.args[0]}"
        )
        exception.args = (msg,) + exception.args[1:]


class PipelineStrategy(AbstractStrategy):
    def __init__(self, pipe: ClusterPipeline):
        super().__init__(pipe)
        self.command_flags = pipe.command_flags

    def execute_command(self, *args, **kwargs):
        return self.pipeline_execute_command(*args, **kwargs)

    def _raise_first_error(self, stack, start_time):
        """
        Raise the first exception on the stack
        """
        for c in stack:
            r = c.result
            if isinstance(r, Exception):
                self.annotate_exception(r, c.position + 1, c.args)

                record_operation_duration(
                    command_name="PIPELINE",
                    duration_seconds=time.monotonic() - start_time,
                    batch_size=len(stack),
                    error=r,
                )

                raise r

    def execute(self, raise_on_error: bool = True) -> List[Any]:
        stack = self._command_queue
        if not stack:
            return []

        try:
            return self.send_cluster_commands(stack, raise_on_error)
        finally:
            self.reset()

    def reset(self):
        """
        Reset back to empty pipeline.
        """
        self._command_queue = []

    def send_cluster_commands(
        self, stack, raise_on_error=True, allow_redirections=True
    ):
        """
        Wrapper for RedisCluster.ERRORS_ALLOW_RETRY errors handling.

        If one of the retryable exceptions has been thrown we assume that:
         - connection_pool was disconnected
         - connection_pool was reset
         - refresh_table_asap set to True

        It will try the number of times specified by
        the retries in config option "self.retry"
        which defaults to 3 unless manually configured.

        If it reaches the number of times, the command will
        raises ClusterDownException.
        """
        if not stack:
            return []
        retry_attempts = self._pipe.retry.get_retries()
        while True:
            try:
                return self._send_cluster_commands(
                    stack,
                    raise_on_error=raise_on_error,
                    allow_redirections=allow_redirections,
                )
            except RedisCluster.ERRORS_ALLOW_RETRY as e:
                if retry_attempts > 0:
                    # Try again with the new cluster setup. All other errors
                    # should be raised.
                    retry_attempts -= 1
                    pass
                else:
                    raise e

    def _send_cluster_commands(
        self, stack, raise_on_error=True, allow_redirections=True
    ):
        """
        Send a bunch of cluster commands to the redis cluster.

        `allow_redirections` If the pipeline should follow
        `ASK` & `MOVED` responses automatically. If set
        to false it will raise RedisClusterException.
        """
        # the first time sending the commands we send all of
        # the commands that were queued up.
        # if we have to run through it again, we only retry
        # the commands that failed.
        attempt = sorted(stack, key=lambda x: x.position)
        is_default_node = False
        # build a list of node objects based on node names we need to
        nodes = {}

        # as we move through each command that still needs to be processed,
        # we figure out the slot number that command maps to, then from
        # the slot determine the node.
        for c in attempt:
            command_policies = self._pipe._policy_resolver.resolve(c.args[0].lower())

            while True:
                # refer to our internal node -> slot table that
                # tells us where a given command should route to.
                # (it might be possible we have a cached node that no longer
                # exists in the cluster, which is why we do this in a loop)
                passed_targets = c.options.pop("target_nodes", None)
                if passed_targets and not self._is_nodes_flag(passed_targets):
                    target_nodes = self._parse_target_nodes(passed_targets)

                    if not command_policies:
                        command_policies = CommandPolicies()
                else:
                    if not command_policies:
                        command = c.args[0].upper()
                        if (
                            len(c.args) >= 2
                            and f"{c.args[0]} {c.args[1]}".upper()
                            in self._pipe.command_flags
                        ):
                            command = f"{c.args[0]} {c.args[1]}".upper()

                        # We only could resolve key properties if command is not
                        # in a list of pre-defined request policies
                        command_flag = self.command_flags.get(command)
                        if not command_flag:
                            # Fallback to default policy
                            if not self._pipe.get_default_node():
                                keys = None
                            else:
                                keys = self._pipe._get_command_keys(*c.args)
                            if not keys or len(keys) == 0:
                                command_policies = CommandPolicies()
                            else:
                                command_policies = CommandPolicies(
                                    request_policy=RequestPolicy.DEFAULT_KEYED,
                                    response_policy=ResponsePolicy.DEFAULT_KEYED,
                                )
                        else:
                            if command_flag in self._pipe._command_flags_mapping:
                                command_policies = CommandPolicies(
                                    request_policy=self._pipe._command_flags_mapping[
                                        command_flag
                                    ]
                                )
                            else:
                                command_policies = CommandPolicies()

                    target_nodes = self._determine_nodes(
                        *c.args,
                        request_policy=command_policies.request_policy,
                        node_flag=passed_targets,
                    )
                    if not target_nodes:
                        raise RedisClusterException(
                            f"No targets were found to execute {c.args} command on"
                        )
                c.command_policies = command_policies
                if len(target_nodes) > 1:
                    raise RedisClusterException(
                        f"Too many targets for command {c.args}"
                    )

                node = target_nodes[0]
                if node == self._pipe.get_default_node():
                    is_default_node = True

                # now that we know the name of the node
                # ( it's just a string in the form of host:port )
                # we can build a list of commands for each node.
                node_name = node.name
                if node_name not in nodes:
                    redis_node = self._pipe.get_redis_connection(node)
                    try:
                        connection = get_connection(redis_node)
                    except (ConnectionError, TimeoutError):
                        for n in nodes.values():
                            n.connection_pool.release(n.connection)
                        # Connection retries are being handled in the node's
                        # Retry object. Reinitialize the node -> slot table.
                        self._nodes_manager.initialize()
                        if is_default_node:
                            self._pipe.replace_default_node()
                        raise
                    nodes[node_name] = NodeCommands(
                        redis_node.parse_response,
                        redis_node.connection_pool,
                        connection,
                    )
                nodes[node_name].append(c)
                break

        # send the commands in sequence.
        # we  write to all the open sockets for each node first,
        # before reading anything
        # this allows us to flush all the requests out across the
        # network
        # so that we can read them from different sockets as they come back.
        # we dont' multiplex on the sockets as they come available,
        # but that shouldn't make too much difference.

        # Start timing for observability
        start_time = time.monotonic()

        try:
            node_commands = nodes.values()
            for n in node_commands:
                n.write()

            for n in node_commands:
                n.read()

                record_operation_duration(
                    command_name="PIPELINE",
                    duration_seconds=time.monotonic() - start_time,
                    server_address=n.connection.host,
                    server_port=n.connection.port,
                    db_namespace=str(n.connection.db),
                    batch_size=len(n.commands),
                )
        finally:
            # release all of the redis connections we allocated earlier
            # back into the connection pool.
            # we used to do this step as part of a try/finally block,
            # but it is really dangerous to
            # release connections back into the pool if for some
            # reason the socket has data still left in it
            # from a previous operation. The write and
            # read operations already have try/catch around them for
            # all known types of errors including connection
            # and socket level errors.
            # So if we hit an exception, something really bad
            # happened and putting any oF
            # these connections back into the pool is a very bad idea.
            # the socket might have unread buffer still sitting in it,
            # and then the next time we read from it we pass the
            # buffered result back from a previous command and
            # every single request after to that connection will always get
            # a mismatched result.
            for n in nodes.values():
                n.connection_pool.release(n.connection)

        # if the response isn't an exception it is a
        # valid response from the node
        # we're all done with that command, YAY!
        # if we have more commands to attempt, we've run into problems.
        # collect all the commands we are allowed to retry.
        # (MOVED, ASK, or connection errors or timeout errors)
        attempt = sorted(
            (
                c
                for c in attempt
                if isinstance(c.result, ClusterPipeline.ERRORS_ALLOW_RETRY)
            ),
            key=lambda x: x.position,
        )
        if attempt and allow_redirections:
            # RETRY MAGIC HAPPENS HERE!
            # send these remaining commands one at a time using `execute_command`
            # in the main client. This keeps our retry logic
            # in one place mostly,
            # and allows us to be more confident in correctness of behavior.
            # at this point any speed gains from pipelining have been lost
            # anyway, so we might as well make the best
            # attempt to get the correct behavior.
            #
            # The client command will handle retries for each
            # individual command sequentially as we pass each
            # one into `execute_command`. Any exceptions
            # that bubble out should only appear once all
            # retries have been exhausted.
            #
            # If a lot of commands have failed, we'll be setting the
            # flag to rebuild the slots table from scratch.
            # So MOVED errors should correct themselves fairly quickly.
            self._pipe.reinitialize_counter += 1
            if self._pipe._should_reinitialized():
                self._nodes_manager.initialize()
                if is_default_node:
                    self._pipe.replace_default_node()
            for c in attempt:
                try:
                    # send each command individually like we
                    # do in the main client.
                    c.result = self._pipe.parent_execute_command(*c.args, **c.options)
                except RedisError as e:
                    c.result = e

        # turn the response back into a simple flat array that corresponds
        # to the sequence of commands issued in the stack in pipeline.execute()
        response = []
        for c in sorted(stack, key=lambda x: x.position):
            if c.args[0] in self._pipe.cluster_response_callbacks:
                # Remove keys entry, it needs only for cache.
                c.options.pop("keys", None)
                c.result = self._pipe._policies_callback_mapping[
                    c.command_policies.response_policy
                ](
                    self._pipe.cluster_response_callbacks[c.args[0]](
                        c.result, **c.options
                    )
                )
            response.append(c.result)

        if raise_on_error:
            self._raise_first_error(stack, start_time)

        return response

    def _is_nodes_flag(self, target_nodes):
        return isinstance(target_nodes, str) and target_nodes in self._pipe.node_flags

    def _parse_target_nodes(self, target_nodes):
        if isinstance(target_nodes, list):
            nodes = target_nodes
        elif isinstance(target_nodes, ClusterNode):
            # Supports passing a single ClusterNode as a variable
            nodes = [target_nodes]
        elif isinstance(target_nodes, dict):
            # Supports dictionaries of the format {node_name: node}.
            # It enables to execute commands with multi nodes as follows:
            # rc.cluster_save_config(rc.get_primaries())
            nodes = target_nodes.values()
        else:
            raise TypeError(
                "target_nodes type can be one of the following: "
                "node_flag (PRIMARIES, REPLICAS, RANDOM, ALL_NODES),"
                "ClusterNode, list<ClusterNode>, or dict<any, ClusterNode>. "
                f"The passed type is {type(target_nodes)}"
            )
        return nodes

    def _determine_nodes(
        self, *args, request_policy: RequestPolicy, **kwargs
    ) -> List["ClusterNode"]:
        # Determine which nodes should be executed the command on.
        # Returns a list of target nodes.
        command = args[0].upper()
        if (
            len(args) >= 2
            and f"{args[0]} {args[1]}".upper() in self._pipe.command_flags
        ):
            command = f"{args[0]} {args[1]}".upper()

        nodes_flag = kwargs.pop("nodes_flag", None)
        if nodes_flag is not None:
            # nodes flag passed by the user
            command_flag = nodes_flag
        else:
            # get the nodes group for this command if it was predefined
            command_flag = self._pipe.command_flags.get(command)

        if command_flag in self._pipe._command_flags_mapping:
            request_policy = self._pipe._command_flags_mapping[command_flag]

        policy_callback = self._pipe._policies_callback_mapping[request_policy]

        if request_policy == RequestPolicy.DEFAULT_KEYED:
            nodes = policy_callback(command, *args)
        elif request_policy == RequestPolicy.MULTI_SHARD:
            nodes = policy_callback(*args, **kwargs)
        elif request_policy == RequestPolicy.DEFAULT_KEYLESS:
            nodes = policy_callback(args[0])
        else:
            nodes = policy_callback()

        if args[0].lower() == "ft.aggregate":
            self._aggregate_nodes = nodes

        return nodes

    def multi(self):
        raise RedisClusterException(
            "method multi() is not supported outside of transactional context"
        )

    def discard(self):
        raise RedisClusterException(
            "method discard() is not supported outside of transactional context"
        )

    def watch(self, *names):
        raise RedisClusterException(
            "method watch() is not supported outside of transactional context"
        )

    def unwatch(self, *names):
        raise RedisClusterException(
            "method unwatch() is not supported outside of transactional context"
        )

    def delete(self, *names):
        if len(names) != 1:
            raise RedisClusterException(
                "deleting multiple keys is not implemented in pipeline command"
            )

        return self.execute_command("DEL", names[0])

    def unlink(self, *names):
        if len(names) != 1:
            raise RedisClusterException(
                "unlinking multiple keys is not implemented in pipeline command"
            )

        return self.execute_command("UNLINK", names[0])


class TransactionStrategy(AbstractStrategy):
    NO_SLOTS_COMMANDS = {"UNWATCH"}
    IMMEDIATE_EXECUTE_COMMANDS = {"WATCH", "UNWATCH"}
    UNWATCH_COMMANDS = {"DISCARD", "EXEC", "UNWATCH"}
    SLOT_REDIRECT_ERRORS = (AskError, MovedError)
    CONNECTION_ERRORS = (
        ConnectionError,
        OSError,
        ClusterDownError,
        SlotNotCoveredError,
    )

    def __init__(self, pipe: ClusterPipeline):
        super().__init__(pipe)
        self._explicit_transaction = False
        self._watching = False
        self._pipeline_slots: Set[int] = set()
        self._transaction_connection: Optional[Connection] = None
        self._executing = False
        self._retry = copy(self._pipe.retry)
        self._retry.update_supported_errors(
            RedisCluster.ERRORS_ALLOW_RETRY + self.SLOT_REDIRECT_ERRORS
        )

    def _get_client_and_connection_for_transaction(self) -> Tuple[Redis, Connection]:
        """
        Find a connection for a pipeline transaction.

        For running an atomic transaction, watch keys ensure that contents have not been
        altered as long as the watch commands for those keys were sent over the same
        connection. So once we start watching a key, we fetch a connection to the
        node that owns that slot and reuse it.
        """
        if not self._pipeline_slots:
            raise RedisClusterException(
                "At least a command with a key is needed to identify a node"
            )

        node: ClusterNode = self._nodes_manager.get_node_from_slot(
            list(self._pipeline_slots)[0], False
        )
        redis_node: Redis = self._pipe.get_redis_connection(node)
        if self._transaction_connection:
            if not redis_node.connection_pool.owns_connection(
                self._transaction_connection
            ):
                previous_node = self._nodes_manager.find_connection_owner(
                    self._transaction_connection
                )
                previous_node.connection_pool.release(self._transaction_connection)
                self._transaction_connection = None

        if not self._transaction_connection:
            self._transaction_connection = get_connection(redis_node)

        return redis_node, self._transaction_connection

    def execute_command(self, *args, **kwargs):
        slot_number: Optional[int] = None
        if args[0] not in ClusterPipeline.NO_SLOTS_COMMANDS:
            slot_number = self._pipe.determine_slot(*args)

        if (
            self._watching or args[0] in self.IMMEDIATE_EXECUTE_COMMANDS
        ) and not self._explicit_transaction:
            if args[0] == "WATCH":
                self._validate_watch()

            if slot_number is not None:
                if self._pipeline_slots and slot_number not in self._pipeline_slots:
                    raise CrossSlotTransactionError(
                        "Cannot watch or send commands on different slots"
                    )

                self._pipeline_slots.add(slot_number)
            elif args[0] not in self.NO_SLOTS_COMMANDS:
                raise RedisClusterException(
                    f"Cannot identify slot number for command: {args[0]},"
                    "it cannot be triggered in a transaction"
                )

            return self._immediate_execute_command(*args, **kwargs)
        else:
            if slot_number is not None:
                self._pipeline_slots.add(slot_number)

            return self.pipeline_execute_command(*args, **kwargs)

    def _validate_watch(self):
        if self._explicit_transaction:
            raise RedisError("Cannot issue a WATCH after a MULTI")

        self._watching = True

    def _immediate_execute_command(self, *args, **options):
        return self._retry.call_with_retry(
            lambda: self._get_connection_and_send_command(*args, **options),
            self._reinitialize_on_error,
            with_failure_count=True,
        )

    def _get_connection_and_send_command(self, *args, **options):
        redis_node, connection = self._get_client_and_connection_for_transaction()

        # Start timing for observability
        start_time = time.monotonic()

        try:
            response = self._send_command_parse_response(
                connection, redis_node, args[0], *args, **options
            )

            record_operation_duration(
                command_name=args[0],
                duration_seconds=time.monotonic() - start_time,
                server_address=connection.host,
                server_port=connection.port,
                db_namespace=str(connection.db),
            )

            return response
        except Exception as e:
            e.connection = connection
            record_operation_duration(
                command_name=args[0],
                duration_seconds=time.monotonic() - start_time,
                server_address=connection.host,
                server_port=connection.port,
                db_namespace=str(connection.db),
                error=e,
            )
            raise

    def _send_command_parse_response(
        self, conn, redis_node: Redis, command_name, *args, **options
    ):
        """
        Send a command and parse the response
        """

        conn.send_command(*args)
        output = redis_node.parse_response(conn, command_name, **options)

        if command_name in self.UNWATCH_COMMANDS:
            self._watching = False
        return output

    def _reinitialize_on_error(self, error, failure_count):
        if hasattr(error, "connection"):
            record_error_count(
                server_address=error.connection.host,
                server_port=error.connection.port,
                network_peer_address=error.connection.host,
                network_peer_port=error.connection.port,
                error_type=error,
                retry_attempts=failure_count,
                is_internal=False,
            )

        if self._watching:
            if type(error) in self.SLOT_REDIRECT_ERRORS and self._executing:
                raise WatchError("Slot rebalancing occurred while watching keys")

        if (
            type(error) in self.SLOT_REDIRECT_ERRORS
            or type(error) in self.CONNECTION_ERRORS
        ):
            if self._transaction_connection:
                # Disconnect and release back to pool
                self._transaction_connection.disconnect()
                node = self._nodes_manager.find_connection_owner(
                    self._transaction_connection
                )
                if node and node.redis_connection:
                    node.redis_connection.connection_pool.release(
                        self._transaction_connection
                    )
                self._transaction_connection = None

            self._pipe.reinitialize_counter += 1
            if self._pipe._should_reinitialized():
                self._nodes_manager.initialize()
                self.reinitialize_counter = 0
            else:
                if isinstance(error, AskError):
                    self._nodes_manager.move_slot(error)

        self._executing = False

    def _raise_first_error(self, responses, stack, start_time):
        """
        Raise the first exception on the stack
        """
        for r, cmd in zip(responses, stack):
            if isinstance(r, Exception):
                self.annotate_exception(r, cmd.position + 1, cmd.args)

                record_operation_duration(
                    command_name="TRANSACTION",
                    duration_seconds=time.monotonic() - start_time,
                    server_address=self._transaction_connection.host,
                    server_port=self._transaction_connection.port,
                    db_namespace=str(self._transaction_connection.db),
                )

                raise r

    def execute(self, raise_on_error: bool = True) -> List[Any]:
        stack = self._command_queue
        if not stack and (not self._watching or not self._pipeline_slots):
            return []

        return self._execute_transaction_with_retries(stack, raise_on_error)

    def _execute_transaction_with_retries(
        self, stack: List["PipelineCommand"], raise_on_error: bool
    ):
        return self._retry.call_with_retry(
            lambda: self._execute_transaction(stack, raise_on_error),
            lambda error, failure_count: self._reinitialize_on_error(
                error, failure_count
            ),
            with_failure_count=True,
        )

    def _execute_transaction(
        self, stack: List["PipelineCommand"], raise_on_error: bool
    ):
        if len(self._pipeline_slots) > 1:
            raise CrossSlotTransactionError(
                "All keys involved in a cluster transaction must map to the same slot"
            )

        self._executing = True

        redis_node, connection = self._get_client_and_connection_for_transaction()

        stack = chain(
            [PipelineCommand(("MULTI",))],
            stack,
            [PipelineCommand(("EXEC",))],
        )
        commands = [c.args for c in stack if EMPTY_RESPONSE not in c.options]
        packed_commands = connection.pack_commands(commands)

        # Start timing for observability
        start_time = time.monotonic()

        connection.send_packed_command(packed_commands)
        errors = []

        # parse off the response for MULTI
        # NOTE: we need to handle ResponseErrors here and continue
        # so that we read all the additional command messages from
        # the socket
        try:
            redis_node.parse_response(connection, "MULTI")
        except ResponseError as e:
            self.annotate_exception(e, 0, "MULTI")
            errors.append(e)
        except self.CONNECTION_ERRORS as cluster_error:
            self.annotate_exception(cluster_error, 0, "MULTI")
            raise

        # and all the other commands
        for i, command in enumerate(self._command_queue):
            if EMPTY_RESPONSE in command.options:
                errors.append((i, command.options[EMPTY_RESPONSE]))
            else:
                try:
                    _ = redis_node.parse_response(connection, "_")
                except self.SLOT_REDIRECT_ERRORS as slot_error:
                    self.annotate_exception(slot_error, i + 1, command.args)
                    errors.append(slot_error)
                except self.CONNECTION_ERRORS as cluster_error:
                    self.annotate_exception(cluster_error, i + 1, command.args)
                    raise
                except ResponseError as e:
                    self.annotate_exception(e, i + 1, command.args)
                    errors.append(e)

        response = None
        # parse the EXEC.
        try:
            response = redis_node.parse_response(connection, "EXEC")
        except ExecAbortError:
            if errors:
                raise errors[0]
            raise

        self._executing = False

        record_operation_duration(
            command_name="TRANSACTION",
            duration_seconds=time.monotonic() - start_time,
            server_address=connection.host,
            server_port=connection.port,
            db_namespace=str(connection.db),
            batch_size=len(self._command_queue),
        )

        # EXEC clears any watched keys
        self._watching = False

        if response is None:
            raise WatchError("Watched variable changed.")

        # put any parse errors into the response
        for i, e in errors:
            response.insert(i, e)

        if len(response) != len(self._command_queue):
            raise InvalidPipelineStack(
                "Unexpected response length for cluster pipeline EXEC."
                " Command stack was {} but response had length {}".format(
                    [c.args[0] for c in self._command_queue], len(response)
                )
            )

        # find any errors in the response and raise if necessary
        if raise_on_error or len(errors) > 0:
            self._raise_first_error(
                response,
                self._command_queue,
                start_time,
            )

        # We have to run response callbacks manually
        data = []
        for r, cmd in zip(response, self._command_queue):
            if not isinstance(r, Exception):
                command_name = cmd.args[0]
                if command_name in self._pipe.cluster_response_callbacks:
                    r = self._pipe.cluster_response_callbacks[command_name](
                        r, **cmd.options
                    )
            data.append(r)
        return data

    def reset(self):
        self._command_queue = []

        # make sure to reset the connection state in the event that we were
        # watching something
        if self._transaction_connection:
            try:
                if self._watching:
                    # call this manually since our unwatch or
                    # immediate_execute_command methods can call reset()
                    self._transaction_connection.send_command("UNWATCH")
                    self._transaction_connection.read_response()
                # we can safely return the connection to the pool here since we're
                # sure we're no longer WATCHing anything
                node = self._nodes_manager.find_connection_owner(
                    self._transaction_connection
                )
                if node and node.redis_connection:
                    node.redis_connection.connection_pool.release(
                        self._transaction_connection
                    )
                self._transaction_connection = None
            except self.CONNECTION_ERRORS:
                # disconnect will also remove any previous WATCHes
                if self._transaction_connection:
                    self._transaction_connection.disconnect()
                    node = self._nodes_manager.find_connection_owner(
                        self._transaction_connection
                    )
                    if node and node.redis_connection:
                        node.redis_connection.connection_pool.release(
                            self._transaction_connection
                        )
                    self._transaction_connection = None

        # clean up the other instance attributes
        self._watching = False
        self._explicit_transaction = False
        self._pipeline_slots = set()
        self._executing = False

    def send_cluster_commands(
        self, stack, raise_on_error=True, allow_redirections=True
    ):
        raise NotImplementedError(
            "send_cluster_commands cannot be executed in transactional context."
        )

    def multi(self):
        if self._explicit_transaction:
            raise RedisError("Cannot issue nested calls to MULTI")
        if self._command_queue:
            raise RedisError(
                "Commands without an initial WATCH have already been issued"
            )
        self._explicit_transaction = True

    def watch(self, *names):
        if self._explicit_transaction:
            raise RedisError("Cannot issue a WATCH after a MULTI")

        return self.execute_command("WATCH", *names)

    def unwatch(self):
        if self._watching:
            return self.execute_command("UNWATCH")

        return True

    def discard(self):
        self.reset()

    def delete(self, *names):
        return self.execute_command("DEL", *names)

    def unlink(self, *names):
        return self.execute_command("UNLINK", *names)
