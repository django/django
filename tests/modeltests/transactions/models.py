"""
15. Transactions

Django handles transactions in three different ways. The default is to commit
each transaction upon a write, but you can decorate a function to get
commit-on-success behavior. Alternatively, you can manage the transaction
manually.
"""

from django.db import models

class Reporter(models.Model):
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)
    email = models.EmailField()

    def __repr__(self):
        return "%s %s" % (self.first_name, self.last_name)

API_TESTS = """
>>> from django.db import connection, transaction

# the default behavior is to autocommit after each save() action
>>> def create_a_reporter_then_fail(first, last):
...     a = Reporter(first_name=first, last_name=last)
...     a.save()
...     raise Exception("I meant to do that")
...
>>> create_a_reporter_then_fail("Alice", "Smith")
Traceback (most recent call last):
    ...
Exception: I meant to do that

# The object created before the exception still exists
>>> Reporter.objects.all()
[Alice Smith]

# the autocommit decorator works exactly the same as the default behavior
>>> autocomitted_create_then_fail = transaction.autocommit(create_a_reporter_then_fail)
>>> autocomitted_create_then_fail("Ben", "Jones")
Traceback (most recent call last):
    ...
Exception: I meant to do that

# Same behavior as before
>>> Reporter.objects.all()
[Alice Smith, Ben Jones]

# With the commit_on_success decorator, the transaction is only comitted if the
# function doesn't throw an exception
>>> committed_on_success = transaction.commit_on_success(create_a_reporter_then_fail)
>>> committed_on_success("Carol", "Doe")
Traceback (most recent call last):
    ...
Exception: I meant to do that

# This time the object never got saved
>>> Reporter.objects.all()
[Alice Smith, Ben Jones]

# If there aren't any exceptions, the data will get saved
>>> def remove_a_reporter():
...     r = Reporter.objects.get(first_name="Alice")
...     r.delete()
...
>>> remove_comitted_on_success = transaction.commit_on_success(remove_a_reporter)
>>> remove_comitted_on_success()
>>> Reporter.objects.all()
[Ben Jones]

# You can manually manage transactions if you really want to, but you
# have to remember to commit/rollback
>>> def manually_managed():
...     r = Reporter(first_name="Carol", last_name="Doe")
...     r.save()
...     transaction.commit()
>>> manually_managed = transaction.commit_manually(manually_managed)
>>> manually_managed()
>>> Reporter.objects.all()
[Ben Jones, Carol Doe]

# If you forget, you'll get bad errors
>>> def manually_managed_mistake():
...     r = Reporter(first_name="David", last_name="Davidson")
...     r.save()
...     # oops, I forgot to commit/rollback!
>>> manually_managed_mistake = transaction.commit_manually(manually_managed_mistake)
>>> manually_managed_mistake()
Traceback (most recent call last):
    ...
TransactionManagementError: Transaction managed block ended with pending COMMIT/ROLLBACK
"""