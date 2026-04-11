from enum import Enum

"Core exceptions raised by the Redis client"


class ExceptionType(Enum):
    NETWORK = "network"
    TLS = "tls"
    AUTH = "auth"
    SERVER = "server"


class RedisError(Exception):
    def __init__(self, *args, status_code: str = None):
        super().__init__(*args)
        self.error_type = ExceptionType.SERVER
        self.status_code = status_code

    def __repr__(self):
        return f"{self.error_type.value}:{self.__class__.__name__}"


class ConnectionError(RedisError):
    def __init__(self, *args, status_code: str = None):
        super().__init__(*args, status_code=status_code)
        self.error_type = ExceptionType.NETWORK


class TimeoutError(RedisError):
    def __init__(self, *args, status_code: str = None):
        super().__init__(*args, status_code=status_code)
        self.error_type = ExceptionType.NETWORK


class AuthenticationError(ConnectionError):
    def __init__(self, *args, status_code: str = None):
        super().__init__(*args, status_code=status_code)
        self.error_type = ExceptionType.AUTH


class AuthorizationError(ConnectionError):
    def __init__(self, *args, status_code: str = None):
        super().__init__(*args, status_code=status_code)
        self.error_type = ExceptionType.AUTH


class BusyLoadingError(ConnectionError):
    def __init__(self, *args, status_code: str = None):
        super().__init__(*args, status_code=status_code)
        self.error_type = ExceptionType.NETWORK


class InvalidResponse(RedisError):
    pass


class ResponseError(RedisError):
    pass


class DataError(RedisError):
    pass


class PubSubError(RedisError):
    pass


class WatchError(RedisError):
    pass


class NoScriptError(ResponseError):
    pass


class OutOfMemoryError(ResponseError):
    """
    Indicates the database is full. Can only occur when either:
      * Redis maxmemory-policy=noeviction
      * Redis maxmemory-policy=volatile* and there are no evictable keys

    For more information see `Memory optimization in Redis <https://redis.io/docs/management/optimization/memory-optimization/#memory-allocation>`_. # noqa
    """

    pass


class ExecAbortError(ResponseError):
    pass


class ReadOnlyError(ResponseError):
    pass


class NoPermissionError(ResponseError):
    def __init__(self, *args, status_code: str = None):
        super().__init__(*args, status_code=status_code)
        self.error_type = ExceptionType.AUTH


class ModuleError(ResponseError):
    pass


class LockError(RedisError, ValueError):
    "Errors acquiring or releasing a lock"

    # NOTE: For backwards compatibility, this class derives from ValueError.
    # This was originally chosen to behave like threading.Lock.

    def __init__(self, message=None, lock_name=None):
        super().__init__(message)
        self.message = message
        self.lock_name = lock_name


class LockNotOwnedError(LockError):
    "Error trying to extend or release a lock that is not owned (anymore)"

    pass


class ChildDeadlockedError(Exception):
    "Error indicating that a child process is deadlocked after a fork()"

    pass


class AuthenticationWrongNumberOfArgsError(ResponseError):
    """
    An error to indicate that the wrong number of args
    were sent to the AUTH command
    """

    def __init__(self, *args, status_code: str = None):
        super().__init__(*args, status_code=status_code)
        self.error_type = ExceptionType.AUTH


class RedisClusterException(Exception):
    """
    Base exception for the RedisCluster client
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.error_type = ExceptionType.SERVER

    def __repr__(self):
        return f"{self.error_type.value}:{self.__class__.__name__}"


class ClusterError(RedisError):
    """
    Cluster errors occurred multiple times, resulting in an exhaustion of the
    command execution TTL
    """

    def __init__(self, *args, status_code: str = None):
        super().__init__(*args, status_code=status_code)
        self.error_type = ExceptionType.SERVER


class ClusterDownError(ClusterError, ResponseError):
    """
    Error indicated CLUSTERDOWN error received from cluster.
    By default Redis Cluster nodes stop accepting queries if they detect there
    is at least a hash slot uncovered (no available node is serving it).
    This way if the cluster is partially down (for example a range of hash
    slots are no longer covered) the entire cluster eventually becomes
    unavailable. It automatically returns available as soon as all the slots
    are covered again.
    """

    def __init__(self, resp, status_code: str = None):
        self.args = (resp,)
        self.message = resp
        self.error_type = ExceptionType.SERVER
        self.status_code = status_code


class AskError(ResponseError):
    """
    Error indicated ASK error received from cluster.
    When a slot is set as MIGRATING, the node will accept all queries that
    pertain to this hash slot, but only if the key in question exists,
    otherwise the query is forwarded using a -ASK redirection to the node that
    is target of the migration.

    src node: MIGRATING to dst node
        get > ASK error
        ask dst node > ASKING command
    dst node: IMPORTING from src node
        asking command only affects next command
        any op will be allowed after asking command
    """

    def __init__(self, resp, status_code: str = None):
        """should only redirect to master node"""
        super().__init__(resp, status_code=status_code)
        self.args = (resp,)
        self.message = resp
        slot_id, new_node = resp.split(" ")
        host, port = new_node.rsplit(":", 1)
        self.slot_id = int(slot_id)
        self.node_addr = self.host, self.port = host, int(port)


class TryAgainError(ResponseError):
    """
    Error indicated TRYAGAIN error received from cluster.
    Operations on keys that don't exist or are - during resharding - split
    between the source and destination nodes, will generate a -TRYAGAIN error.
    """

    def __init__(self, *args, status_code: str = None, **kwargs):
        super().__init__(*args, status_code=status_code)


class ClusterCrossSlotError(ResponseError):
    """
    Error indicated CROSSSLOT error received from cluster.
    A CROSSSLOT error is generated when keys in a request don't hash to the
    same slot.
    """

    message = "Keys in request don't hash to the same slot"

    def __init__(self, *args, status_code: str = None):
        super().__init__(*args, status_code=status_code)
        self.error_type = ExceptionType.SERVER


class MovedError(AskError):
    """
    Error indicated MOVED error received from cluster.
    A request sent to a node that doesn't serve this key will be replayed with
    a MOVED error that points to the correct node.
    """

    pass


class MasterDownError(ClusterDownError):
    """
    Error indicated MASTERDOWN error received from cluster.
    Link with MASTER is down and replica-serve-stale-data is set to 'no'.
    """

    pass


class SlotNotCoveredError(RedisClusterException):
    """
    This error only happens in the case where the connection pool will try to
    fetch what node that is covered by a given slot.

    If this error is raised the client should drop the current node layout and
    attempt to reconnect and refresh the node layout again
    """

    pass


class MaxConnectionsError(ConnectionError):
    """
    Raised when a connection pool has reached its max_connections limit.
    This indicates pool exhaustion rather than an actual connection failure.
    """

    pass


class CrossSlotTransactionError(RedisClusterException):
    """
    Raised when a transaction or watch is triggered in a pipeline
    and not all keys or all commands belong to the same slot.
    """

    pass


class InvalidPipelineStack(RedisClusterException):
    """
    Raised on unexpected response length on pipelines. This is
    most likely a handling error on the stack.
    """

    pass


class ExternalAuthProviderError(ConnectionError):
    """
    Raised when an external authentication provider returns an error.
    """

    pass


class IncorrectPolicyType(Exception):
    """
    Raised when a policy type isn't matching to any known policy types.
    """

    pass
