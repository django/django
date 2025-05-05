from contextlib import AsyncContextDecorator, ContextDecorator, contextmanager
from django.utils.sync_async import run_async_generator, run_sync_generator

from django.db import (
    DEFAULT_DB_ALIAS,
    DatabaseError,
    Error,
    ProgrammingError,
    connections,
    async_connections,
)


class TransactionManagementError(ProgrammingError):
    """Transaction management is used improperly."""

    pass


def get_connection(using=None):
    """
    Get a database connection by name, or the default database connection
    if no name is provided. This is a private API.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    return connections[using]


def aget_connection(using=None):
    """
    Get a async database connection by name, or the default database connection
    if no name is provided. This is a private API.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    return async_connections[using]


def get_autocommit(using=None):
    """Get the autocommit status of the connection."""
    return get_connection(using).get_autocommit()


def set_autocommit(autocommit, using=None):
    """Set the autocommit status of the connection."""
    return get_connection(using).set_autocommit(autocommit)


def commit(using=None):
    """Commit a transaction."""
    get_connection(using).commit()


def rollback(using=None):
    """Roll back a transaction."""
    get_connection(using).rollback()


def savepoint(using=None):
    """
    Create a savepoint (if supported and required by the backend) inside the
    current transaction. Return an identifier for the savepoint that will be
    used for the subsequent rollback or commit.
    """
    return get_connection(using).savepoint()


def savepoint_rollback(sid, using=None):
    """
    Roll back the most recent savepoint (if one exists). Do nothing if
    savepoints are not supported.
    """
    get_connection(using).savepoint_rollback(sid)


def savepoint_commit(sid, using=None):
    """
    Commit the most recent savepoint (if one exists). Do nothing if
    savepoints are not supported.
    """
    get_connection(using).savepoint_commit(sid)


def clean_savepoints(using=None):
    """
    Reset the counter used to generate unique savepoint ids in this thread.
    """
    get_connection(using).clean_savepoints()


def get_rollback(using=None):
    """Get the "needs rollback" flag -- for *advanced use* only."""
    return get_connection(using).get_rollback()


def set_rollback(rollback, using=None):
    """
    Set or unset the "needs rollback" flag -- for *advanced use* only.

    When `rollback` is `True`, trigger a rollback when exiting the innermost
    enclosing atomic block that has `savepoint=True` (that's the default). Use
    this to force a rollback without raising an exception.

    When `rollback` is `False`, prevent such a rollback. Use this only after
    rolling back to a known-good state! Otherwise, you break the atomic block
    and data corruption may occur.
    """
    return get_connection(using).set_rollback(rollback)


async def aset_rollback(rollback, using=None):
    return aget_connection(using).set_rollback(rollback)


@contextmanager
def mark_for_rollback_on_error(using=None):
    """
    Internal low-level utility to mark a transaction as "needs rollback" when
    an exception is raised while not enforcing the enclosed block to be in a
    transaction. This is needed by Model.save() and friends to avoid starting a
    transaction when in autocommit mode and a single query is executed.

    It's equivalent to:

        connection = get_connection(using)
        if connection.get_autocommit():
            yield
        else:
            with transaction.atomic(using=using, savepoint=False):
                yield

    but it uses low-level utilities to avoid performance overhead.
    """
    try:
        yield
    except Exception as exc:
        connection = get_connection(using)
        if connection.in_atomic_block:
            connection.needs_rollback = True
            connection.rollback_exc = exc
        raise


def on_commit(func, using=None, robust=False):
    """
    Register `func` to be called when the current transaction is committed.
    If the current transaction is rolled back, `func` will not be called.
    """
    get_connection(using).on_commit(func, robust)


#################################
# Decorators / context managers #
#################################

class BaseAtomic:
    """
    Guarantee the atomic execution of a given block.

    An instance can be used either as a decorator or as a context manager.

    When it's used as a decorator, __call__ wraps the execution of the
    decorated function in the instance itself, used as a context manager.

    When it's used as a context manager, __enter__ creates a transaction or a
    savepoint, depending on whether a transaction is already in progress, and
    __exit__ commits the transaction or releases the savepoint on normal exit,
    and rolls back the transaction or to the savepoint on exceptions.

    It's possible to disable the creation of savepoints if the goal is to
    ensure that some code runs within a transaction without creating overhead.

    A stack of savepoint identifiers is maintained as an attribute of the
    connection. None denotes the absence of a savepoint.

    This allows reentrancy even if the same AtomicWrapper is reused. For
    example, it's possible to define `oa = atomic('other')` and use `@oa` or
    `with oa:` multiple times.

    Since database connections are thread-local, this is thread-safe.

    An atomic block can be tagged as durable. In this case, a RuntimeError is
    raised if it's nested within another atomic block. This guarantees
    that database changes in a durable block are committed to the database when
    the block exits without error.

    This is a private API.
    """

    def __init__(self, using, savepoint, durable):
        self.using = using
        self.savepoint = savepoint
        self.durable = durable
        self._from_testcase = False

    def get_connection(self, using):
        raise NotImplementedError

    def enter_gen(self):
        connection = yield self.get_connection(self.using)

        if (
            self.durable
            and connection.atomic_blocks
            and not connection.atomic_blocks[-1]._from_testcase
        ):
            raise RuntimeError(
                "A durable atomic block cannot be nested within another "
                "atomic block."
            )

        if not connection.in_atomic_block:
            # Reset state when entering an outermost atomic block.
            connection.commit_on_exit = True
            connection.needs_rollback = False

            atomic_state = yield connection.get_autocommit()

            if not atomic_state:
                # Pretend we're already in an atomic block to bypass the code
                # that disables autocommit to enter a transaction, and make a
                # note to deal with this case in __exit__.
                connection.in_atomic_block = True
                connection.commit_on_exit = False

        if connection.in_atomic_block:
            # We're already in a transaction; create a savepoint, unless we
            # were told not to or we're already waiting for a rollback. The
            # second condition avoids creating useless savepoints and prevents
            # overwriting needs_rollback until the rollback is performed.
            if self.savepoint and not connection.needs_rollback:
                sid = yield connection.savepoint()
                connection.savepoint_ids.append(sid)
            else:
                connection.savepoint_ids.append(None)
        else:
            yield connection.set_autocommit(
                False, force_begin_transaction_with_broken_autocommit=True
            )
            connection.in_atomic_block = True

        if connection.in_atomic_block:
            connection.atomic_blocks.append(self)

    def exit_gen(self, exc_type, exc_value, traceback):
        connection = yield self.get_connection(self.using)

        if connection.in_atomic_block:
            connection.atomic_blocks.pop()

        if connection.savepoint_ids:
            sid = connection.savepoint_ids.pop()
        else:
            # Prematurely unset this flag to allow using commit or rollback.
            connection.in_atomic_block = False

        try:
            if connection.closed_in_transaction:
                # The database will perform a rollback by itself.
                # Wait until we exit the outermost block.
                pass

            elif exc_type is None and not connection.needs_rollback:
                if connection.in_atomic_block:
                    # Release savepoint if there is one
                    if sid is not None:
                        try:
                            yield connection.savepoint_commit(sid)
                        except DatabaseError:
                            try:
                                yield connection.savepoint_rollback(sid)
                                # The savepoint won't be reused. Release it to
                                # minimize overhead for the database server.
                                yield connection.savepoint_commit(sid)
                            except Error:
                                # If rolling back to a savepoint fails, mark for
                                # rollback at a higher level and avoid shadowing
                                # the original exception.
                                connection.needs_rollback = True
                            raise
                else:
                    # Commit transaction
                    try:
                        yield connection.commit()
                    except DatabaseError:
                        try:
                            yield connection.rollback()
                        except Error:
                            # An error during rollback means that something
                            # went wrong with the connection. Drop it.
                            yield connection.close()
                        raise
            else:
                # This flag will be set to True again if there isn't a savepoint
                # allowing to perform the rollback at this level.
                connection.needs_rollback = False
                if connection.in_atomic_block:
                    # Roll back to savepoint if there is one, mark for rollback
                    # otherwise.
                    if sid is None:
                        connection.needs_rollback = True
                    else:
                        try:
                            yield connection.savepoint_rollback(sid)
                            # The savepoint won't be reused. Release it to
                            # minimize overhead for the database server.
                            yield connection.savepoint_commit(sid)
                        except Error:
                            # If rolling back to a savepoint fails, mark for
                            # rollback at a higher level and avoid shadowing
                            # the original exception.
                            connection.needs_rollback = True
                else:
                    # Roll back transaction
                    try:
                        yield connection.rollback()
                    except Error:
                        # An error during rollback means that something
                        # went wrong with the connection. Drop it.
                        yield connection.close()

        finally:
            # Outermost block exit when autocommit was enabled.
            if not connection.in_atomic_block:
                if connection.closed_in_transaction:
                    connection.connection = None
                else:
                    yield connection.set_autocommit(True)
            # Outermost block exit when autocommit was disabled.
            elif not connection.savepoint_ids and not connection.commit_on_exit:
                if connection.closed_in_transaction:
                    connection.connection = None
                else:
                    connection.in_atomic_block = False


class Atomic(ContextDecorator, BaseAtomic):
    def get_connection(self, using):
        return get_connection(using)

    def __enter__(self):
        run_sync_generator(self.enter_gen())

    def __exit__(self, exc_type, exc_value, traceback):
        run_sync_generator(self.exit_gen(exc_type, exc_value, traceback))


class AsyncAtomic(AsyncContextDecorator, BaseAtomic):
    def get_connection(self, using):
        connection = aget_connection(using)
        return connection

    async def __aenter__(self):
        await run_async_generator(self.enter_gen())

    async def __aexit__(self, exc_type, exc_value, traceback):
        await run_async_generator(self.exit_gen(exc_type, exc_value, traceback))


def atomic(using=None, savepoint=True, durable=False):
    # Bare decorator: @atomic -- although the first argument is called
    # `using`, it's actually the function being decorated.
    if callable(using):
        return Atomic(DEFAULT_DB_ALIAS, savepoint, durable)(using)
    # Decorator: @atomic(...) or context manager: with atomic(...): ...
    else:
        return Atomic(using, savepoint, durable)


def async_atomic(using=None, savepoint=True, durable=False):
    # Bare decorator: @async_atomic -- although the first argument is called
    # `using`, it's actually the function being decorated.
    if callable(using):
        return AsyncAtomic(DEFAULT_DB_ALIAS, savepoint, durable)(using)
    # Decorator: @async_atomic(...) or context manager: with async_atomic(...): ...
    else:
        return AsyncAtomic(using, savepoint, durable)


def _non_atomic_requests(view, using):
    try:
        view._non_atomic_requests.add(using)
    except AttributeError:
        view._non_atomic_requests = {using}
    return view


def non_atomic_requests(using=None):
    if callable(using):
        return _non_atomic_requests(using, DEFAULT_DB_ALIAS)
    else:
        if using is None:
            using = DEFAULT_DB_ALIAS
        return lambda view: _non_atomic_requests(view, using)
