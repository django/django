from django.db import transaction

class TransactionMiddleware(object):
    """
    Transaction middleware. If this is enabled, each view function will be run
    with commit_on_response activated - that way a save() doesn't do a direct
    commit, the commit is done when a successful response is created. If an
    exception happens, the database is rolled back.
    """
    def process_request(self, request):
        """Enters transaction management"""
        transaction.enter_transaction_management()
        transaction.managed(True)

    def process_exception(self, request, exception):
        """Rolls back the database and leaves transaction management"""
        if transaction.is_dirty():
            # This rollback might fail because of network failure for example.
            # If rollback isn't possible it is impossible to clean the
            # connection's state. So leave the connection in dirty state and
            # let request_finished signal deal with cleaning the connection.
            transaction.rollback()
        transaction.leave_transaction_management()

    def process_response(self, request, response):
        """Commits and leaves transaction management."""
        if transaction.is_managed():
            if transaction.is_dirty():
                # Note: it is possible that the commit fails. If the reason is
                # closed connection or some similar reason, then there is
                # little hope to proceed nicely. However, in some cases (
                # deferred foreign key checks for exampl) it is still possible
                # to rollback().
                try:
                    transaction.commit()
                except Exception:
                    # If the rollback fails, the transaction state will be
                    # messed up. It doesn't matter, the connection will be set
                    # to clean state after the request finishes. And, we can't
                    # clean the state here properly even if we wanted to, the
                    # connection is in transaction but we can't rollback...
                    transaction.rollback()
                    transaction.leave_transaction_management()
                    raise
            transaction.leave_transaction_management()
        return response
