from django.conf import settings
from django.db import transaction

class TransactionMiddleware:
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
            transaction.rollback()
        transaction.leave_transaction_management()

    def process_response(self, request, response):
        """Commits and leaves transaction management."""
        if transaction.is_managed():
            if transaction.is_dirty():
                transaction.commit()
            transaction.leave_transaction_management()
        return response
