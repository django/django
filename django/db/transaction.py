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

import thread
from django.db import connection
from django.conf import settings

class TransactionManagementError(Exception):
    """
    This is the exception that is thrown when
    something bad happens with transaction management.
    """
    pass
    
# The state is a dictionary of lists. The key to the dict is the current
# thread and the list is handled as a stack of values.
state = {}

# The dirty flag is set by *_unless_managed functions to denote that the
# code under transaction management has changed things to require a
# database commit.
dirty = {}

def enter_transaction_management():
    """
    Enters transaction management for a running thread. It must be balanced with
    the appropriate leave_transaction_management call, since the actual state is
    managed as a stack.
    
     The state and dirty flag are carried over from the surrounding block or
    from the settings, if there is no surrounding block (dirty is allways false
    when no current block is running).
    """
    thread_ident = thread.get_ident()
    if state.has_key(thread_ident) and state[thread_ident]:
        state[thread_ident].append(state[thread_ident][-1])
    else:
        state[thread_ident] = []
        state[thread_ident].append(settings.TRANSACTIONS_MANAGED)
    if not dirty.has_key(thread_ident):
        dirty[thread_ident] = False

def leave_transaction_management():
    """
    Leaves transaction management for a running thread. A dirty flag is carried
    over to the surrounding block, as a commit will commit all changes, even
    those from outside (commits are on connection level).
    """
    thread_ident = thread.get_ident()
    if state.has_key(thread_ident) and state[thread_ident]:
        del state[thread_ident][-1]
    else:
        raise TransactionManagementError("This code isn't under transaction management")
    if dirty.get(thread_ident, False):
        # I fixed it for you this time, but don't do it again!
        rollback()
        raise TransactionManagementError("Transaction managed block ended with pending COMMIT/ROLLBACK")
    dirty[thread_ident] = False

def is_dirty():
    """
    Checks if the current transaction requires a commit for changes to happen.
    """
    return dirty.get(thread.get_ident(), False)

def set_dirty():
    """
    Sets a dirty flag for the current thread and code streak. This can be used
    to decide in a managed block of code to decide whether there are open
    changes waiting for commit.
    """
    thread_ident = thread.get_ident()
    if dirty.has_key(thread_ident):
        dirty[thread_ident] = True
    else:
        raise TransactionManagementError("This code isn't under transaction management")

def set_clean():
    """
    Resets a dirty flag for the current thread and code streak. This can be used
    to decide in a managed block of code to decide whether there should happen a
    commit or rollback.
    """
    thread_ident = thread.get_ident()
    if dirty.has_key(thread_ident):
        dirty[thread_ident] = False
    else:
        raise TransactionManagementError("This code isn't under transaction management")

def is_managed():
    """
    Checks whether the transaction manager is in manual or in auto state.
    """
    thread_ident = thread.get_ident()
    if state.has_key(thread_ident):
        if state[thread_ident]:
            return state[thread_ident][-1]
    return settings.TRANSACTIONS_MANAGED

def managed(flag=True):
    """
    Puts the transaction manager into a manual state - managed transactions have
    to be committed explicitely by the user. If you switch off transaction
    management and there is a pending commit/rollback, the data will be
    commited.
    """
    thread_ident = thread.get_ident()
    top = state.get(thread_ident, None)
    if top:
        top[-1] = flag
        if not flag and is_dirty():
            connection._commit()
            set_clean()
    else:
        raise TransactionManagementError("This code isn't under transaction management")

def commit_unless_managed():
    """
    Commits changes if the system is not in managed transaction mode.
    """
    if not is_managed():
        connection._commit()
    else:
        set_dirty()

def rollback_unless_managed():
    """
    Rolls back changes if the system is not in managed transaction mode.
    """
    if not is_managed():
        connection._rollback()
    else:
        set_dirty()

def commit():
    """
    Does the commit itself and resets the dirty flag.
    """
    connection._commit()
    set_clean()

def rollback():
    """
    This function does the rollback itself and resets the dirty flag.
    """
    connection._rollback()
    set_clean()

##############
# DECORATORS #
##############

def autocommit(func):
    """
    Decorator that activates commit on save. This is Django's default behavour;
    this decorator is useful if you globally activated transaction management in
    your settings file and want the default behaviour in some view functions.
    """

    def _autocommit(*args, **kw):
        try:
            enter_transaction_management()
            managed(False)
            return func(*args, **kw)
        finally:
            leave_transaction_management()

    return _autocommit

def commit_on_success(func):
    """
    This decorator activates commit on response. This way if the viewfunction
    runs successfully, a commit is made, if the viewfunc produces an exception,
    a rollback is made. This is one of the most common ways to do transaction
    control in web apps.
    """

    def _commit_on_success(*args, **kw):
        try:
            enter_transaction_management()
            managed(True)
            try:
                res = func(*args, **kw)
            except Exception, e:
                if is_dirty():
                    rollback()
                raise e
            else:
                if is_dirty():
                    commit()
            return res
        finally:
            leave_transaction_management()
            
    return _commit_on_success

def commit_manually(func):
    """
    Decorator that activates manual transaction control. It just disables
    automatic transaction control and doesn't do any commit/rollback of it's own
    - it's up to the user to call the commit and rollback functions themselves.
    """

    def _commit_manually(*args, **kw):
        try:
            enter_transaction_management()
            managed(True)
            return func(*args, **kw)
        finally:
            leave_transaction_management()

    return _commit_manually


