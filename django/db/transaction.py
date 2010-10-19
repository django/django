"""
This module implements a transaction manager that can be used to define
transaction handling in a request or view function. It is used by transaction
control middleware and decorators.

The transaction manager can be in managed or in auto state. Auto state means the
system is using a commit-on-save strategy (actually it's more like
commit-on-change). As soon as the .save() or .delete() (or related) methods are
called, a commit is made.

Managed transactions don't do those commits, but will need some kind of manual
or implicit commits or rollbacks.
"""
import sys

try:
    import thread
except ImportError:
    import dummy_thread as thread
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.4 fallback.

from django.conf import settings
from django.db import connections, DEFAULT_DB_ALIAS

class TransactionManagementError(Exception):
    """
    This exception is thrown when something bad happens with transaction
    management.
    """
    pass

# The states are dictionaries of dictionaries of lists. The key to the outer
# dict is the current thread, and the key to the inner dictionary is the
# connection alias and the list is handled as a stack of values.
state = {}
savepoint_state = {}

# The dirty flag is set by *_unless_managed functions to denote that the
# code under transaction management has changed things to require a
# database commit.
# This is a dictionary mapping thread to a dictionary mapping connection
# alias to a boolean.
dirty = {}

def enter_transaction_management(managed=True, using=None):
    """
    Enters transaction management for a running thread. It must be balanced with
    the appropriate leave_transaction_management call, since the actual state is
    managed as a stack.

    The state and dirty flag are carried over from the surrounding block or
    from the settings, if there is no surrounding block (dirty is always false
    when no current block is running).
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    thread_ident = thread.get_ident()
    if thread_ident in state and state[thread_ident].get(using):
        state[thread_ident][using].append(state[thread_ident][using][-1])
    else:
        state.setdefault(thread_ident, {})
        state[thread_ident][using] = [settings.TRANSACTIONS_MANAGED]
    if thread_ident not in dirty or using not in dirty[thread_ident]:
        dirty.setdefault(thread_ident, {})
        dirty[thread_ident][using] = False
    connection._enter_transaction_management(managed)

def leave_transaction_management(using=None):
    """
    Leaves transaction management for a running thread. A dirty flag is carried
    over to the surrounding block, as a commit will commit all changes, even
    those from outside. (Commits are on connection level.)
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection._leave_transaction_management(is_managed(using=using))
    thread_ident = thread.get_ident()
    if thread_ident in state and state[thread_ident].get(using):
        del state[thread_ident][using][-1]
    else:
        raise TransactionManagementError("This code isn't under transaction management")
    if dirty.get(thread_ident, {}).get(using, False):
        rollback(using=using)
        raise TransactionManagementError("Transaction managed block ended with pending COMMIT/ROLLBACK")
    dirty[thread_ident][using] = False

def is_dirty(using=None):
    """
    Returns True if the current transaction requires a commit for changes to
    happen.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    return dirty.get(thread.get_ident(), {}).get(using, False)

def set_dirty(using=None):
    """
    Sets a dirty flag for the current thread and code streak. This can be used
    to decide in a managed block of code to decide whether there are open
    changes waiting for commit.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    thread_ident = thread.get_ident()
    if thread_ident in dirty and using in dirty[thread_ident]:
        dirty[thread_ident][using] = True
    else:
        raise TransactionManagementError("This code isn't under transaction management")

def set_clean(using=None):
    """
    Resets a dirty flag for the current thread and code streak. This can be used
    to decide in a managed block of code to decide whether a commit or rollback
    should happen.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    thread_ident = thread.get_ident()
    if thread_ident in dirty and using in dirty[thread_ident]:
        dirty[thread_ident][using] = False
    else:
        raise TransactionManagementError("This code isn't under transaction management")
    clean_savepoints(using=using)

def clean_savepoints(using=None):
    if using is None:
        using = DEFAULT_DB_ALIAS
    thread_ident = thread.get_ident()
    if thread_ident in savepoint_state and using in savepoint_state[thread_ident]:
        del savepoint_state[thread_ident][using]

def is_managed(using=None):
    """
    Checks whether the transaction manager is in manual or in auto state.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    thread_ident = thread.get_ident()
    if thread_ident in state and using in state[thread_ident]:
        if state[thread_ident][using]:
            return state[thread_ident][using][-1]
    return settings.TRANSACTIONS_MANAGED

def managed(flag=True, using=None):
    """
    Puts the transaction manager into a manual state: managed transactions have
    to be committed explicitly by the user. If you switch off transaction
    management and there is a pending commit/rollback, the data will be
    commited.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    thread_ident = thread.get_ident()
    top = state.get(thread_ident, {}).get(using, None)
    if top:
        top[-1] = flag
        if not flag and is_dirty(using=using):
            connection._commit()
            set_clean(using=using)
    else:
        raise TransactionManagementError("This code isn't under transaction management")

def commit_unless_managed(using=None):
    """
    Commits changes if the system is not in managed transaction mode.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    if not is_managed(using=using):
        connection._commit()
        clean_savepoints(using=using)
    else:
        set_dirty(using=using)

def rollback_unless_managed(using=None):
    """
    Rolls back changes if the system is not in managed transaction mode.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    if not is_managed(using=using):
        connection._rollback()
    else:
        set_dirty(using=using)

def commit(using=None):
    """
    Does the commit itself and resets the dirty flag.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection._commit()
    set_clean(using=using)

def rollback(using=None):
    """
    This function does the rollback itself and resets the dirty flag.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    connection._rollback()
    set_clean(using=using)

def savepoint(using=None):
    """
    Creates a savepoint (if supported and required by the backend) inside the
    current transaction. Returns an identifier for the savepoint that will be
    used for the subsequent rollback or commit.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    thread_ident = thread.get_ident()
    if thread_ident in savepoint_state and using in savepoint_state[thread_ident]:
        savepoint_state[thread_ident][using].append(None)
    else:
        savepoint_state.setdefault(thread_ident, {})
        savepoint_state[thread_ident][using] = [None]
    tid = str(thread_ident).replace('-', '')
    sid = "s%s_x%d" % (tid, len(savepoint_state[thread_ident][using]))
    connection._savepoint(sid)
    return sid

def savepoint_rollback(sid, using=None):
    """
    Rolls back the most recent savepoint (if one exists). Does nothing if
    savepoints are not supported.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    thread_ident = thread.get_ident()
    if thread_ident in savepoint_state and using in savepoint_state[thread_ident]:
        connection._savepoint_rollback(sid)

def savepoint_commit(sid, using=None):
    """
    Commits the most recent savepoint (if one exists). Does nothing if
    savepoints are not supported.
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    connection = connections[using]
    thread_ident = thread.get_ident()
    if thread_ident in savepoint_state and using in savepoint_state[thread_ident]:
        connection._savepoint_commit(sid)

##############
# DECORATORS #
##############

class Transaction(object):
    """
    Acts as either a decorator, or a context manager.  If it's a decorator it
    takes a function and returns a wrapped function.  If it's a contextmanager
    it's used with the ``with`` statement.  In either event entering/exiting
    are called before and after, respectively, the function/block is executed.

    autocommit, commit_on_success, and commit_manually contain the
    implementations of entering and exiting.
    """
    def __init__(self, entering, exiting, using):
        self.entering = entering
        self.exiting = exiting
        self.using = using

    def __enter__(self):
        self.entering(self.using)

    def __exit__(self, exc_type, exc_value, traceback):
        self.exiting(exc_value, self.using)

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            # Once we drop support for Python 2.4 this block should become:
            # with self:
            #     func(*args, **kwargs)
            self.__enter__()
            try:
                res = func(*args, **kwargs)
            except:
                self.__exit__(*sys.exc_info())
                raise
            else:
                self.__exit__(None, None, None)
                return res
        return inner

def _transaction_func(entering, exiting, using):
    """
    Takes 3 things, an entering function (what to do to start this block of
    transaction management), an exiting function (what to do to end it, on both
    success and failure, and using which can be: None, indiciating using is
    DEFAULT_DB_ALIAS, a callable, indicating that using is DEFAULT_DB_ALIAS and
    to return the function already wrapped.

    Returns either a Transaction objects, which is both a decorator and a
    context manager, or a wrapped function, if using is a callable.
    """
    # Note that although the first argument is *called* `using`, it
    # may actually be a function; @autocommit and @autocommit('foo')
    # are both allowed forms.
    if using is None:
        using = DEFAULT_DB_ALIAS
    if callable(using):
        return Transaction(entering, exiting, DEFAULT_DB_ALIAS)(using)
    return Transaction(entering, exiting, using)


def autocommit(using=None):
    """
    Decorator that activates commit on save. This is Django's default behavior;
    this decorator is useful if you globally activated transaction management in
    your settings file and want the default behavior in some view functions.
    """
    def entering(using):
        enter_transaction_management(managed=False, using=using)
        managed(False, using=using)

    def exiting(exc_value, using):
        leave_transaction_management(using=using)

    return _transaction_func(entering, exiting, using)

def commit_on_success(using=None):
    """
    This decorator activates commit on response. This way, if the view function
    runs successfully, a commit is made; if the viewfunc produces an exception,
    a rollback is made. This is one of the most common ways to do transaction
    control in Web apps.
    """
    def entering(using):
        enter_transaction_management(using=using)
        managed(True, using=using)

    def exiting(exc_value, using):
        if exc_value is not None:
            if is_dirty(using=using):
                rollback(using=using)
        else:
            if is_dirty(using=using):
                try:
                    commit(using=using)
                except:
                    rollback(using=using)
                    raise

    return _transaction_func(entering, exiting, using)

def commit_manually(using=None):
    """
    Decorator that activates manual transaction control. It just disables
    automatic transaction control and doesn't do any commit/rollback of its
    own -- it's up to the user to call the commit and rollback functions
    themselves.
    """
    def entering(using):
        enter_transaction_management(using=using)
        managed(True, using=using)

    def exiting(exc_value, using):
        leave_transaction_management(using=using)

    return _transaction_func(entering, exiting, using)
