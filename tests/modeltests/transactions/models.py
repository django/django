"""
15. Transactions

Django handles transactions in three different ways. The default is to commit
each transaction upon a write, but you can decorate a function to get
commit-on-success behavior. Alternatively, you can manage the transaction
manually.
"""

from django.db import models, DEFAULT_DB_ALIAS

class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()

    class Meta:
        ordering = ('first_name', 'last_name')

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)

__test__ = {'API_TESTS':"""
>>> from django.db import connection, transaction
"""}

from django.conf import settings

building_docs = getattr(settings, 'BUILDING_DOCS', False)

if building_docs or settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] != 'django.db.backends.mysql':
    __test__['API_TESTS'] += """
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
[<Reporter: Alice Smith>]

# the autocommit decorator works exactly the same as the default behavior
>>> autocomitted_create_then_fail = transaction.autocommit(create_a_reporter_then_fail)
>>> autocomitted_create_then_fail("Ben", "Jones")
Traceback (most recent call last):
    ...
Exception: I meant to do that

# Same behavior as before
>>> Reporter.objects.all()
[<Reporter: Alice Smith>, <Reporter: Ben Jones>]

# the autocommit decorator also works with a using argument
>>> using_autocomitted_create_then_fail = transaction.autocommit(using='default')(create_a_reporter_then_fail)
>>> using_autocomitted_create_then_fail("Carol", "Doe")
Traceback (most recent call last):
    ...
Exception: I meant to do that

# Same behavior as before
>>> Reporter.objects.all()
[<Reporter: Alice Smith>, <Reporter: Ben Jones>, <Reporter: Carol Doe>]

# With the commit_on_success decorator, the transaction is only committed if the
# function doesn't throw an exception
>>> committed_on_success = transaction.commit_on_success(create_a_reporter_then_fail)
>>> committed_on_success("Dirk", "Gently")
Traceback (most recent call last):
    ...
Exception: I meant to do that

# This time the object never got saved
>>> Reporter.objects.all()
[<Reporter: Alice Smith>, <Reporter: Ben Jones>, <Reporter: Carol Doe>]

# commit_on_success decorator also works with a using argument
>>> using_committed_on_success = transaction.commit_on_success(using='default')(create_a_reporter_then_fail)
>>> using_committed_on_success("Dirk", "Gently")
Traceback (most recent call last):
    ...
Exception: I meant to do that

# This time the object never got saved
>>> Reporter.objects.all()
[<Reporter: Alice Smith>, <Reporter: Ben Jones>, <Reporter: Carol Doe>]

# If there aren't any exceptions, the data will get saved
>>> def remove_a_reporter():
...     r = Reporter.objects.get(first_name="Alice")
...     r.delete()
...
>>> remove_comitted_on_success = transaction.commit_on_success(remove_a_reporter)
>>> remove_comitted_on_success()
>>> Reporter.objects.all()
[<Reporter: Ben Jones>, <Reporter: Carol Doe>]

# You can manually manage transactions if you really want to, but you
# have to remember to commit/rollback
>>> def manually_managed():
...     r = Reporter(first_name="Dirk", last_name="Gently")
...     r.save()
...     transaction.commit()
>>> manually_managed = transaction.commit_manually(manually_managed)
>>> manually_managed()
>>> Reporter.objects.all()
[<Reporter: Ben Jones>, <Reporter: Carol Doe>, <Reporter: Dirk Gently>]

# If you forget, you'll get bad errors
>>> def manually_managed_mistake():
...     r = Reporter(first_name="Edward", last_name="Woodward")
...     r.save()
...     # oops, I forgot to commit/rollback!
>>> manually_managed_mistake = transaction.commit_manually(manually_managed_mistake)
>>> manually_managed_mistake()
Traceback (most recent call last):
    ...
TransactionManagementError: Transaction managed block ended with pending COMMIT/ROLLBACK

# commit_manually also works with a using argument
>>> using_manually_managed_mistake = transaction.commit_manually(using='default')(manually_managed_mistake)
>>> using_manually_managed_mistake()
Traceback (most recent call last):
    ...
TransactionManagementError: Transaction managed block ended with pending COMMIT/ROLLBACK

"""

# Regression for #11900: If a function wrapped by commit_on_success writes a
# transaction that can't be committed, that transaction should be rolled back.
# The bug is only visible using the psycopg2 backend, though
# the fix is generally a good idea.
pgsql_backends = ('django.db.backends.postgresql_psycopg2', 'postgresql_psycopg2',)
if building_docs or settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] in pgsql_backends:
    __test__['API_TESTS'] += """
>>> def execute_bad_sql():
...     cursor = connection.cursor()
...     cursor.execute("INSERT INTO transactions_reporter (first_name, last_name) VALUES ('Douglas', 'Adams');")
...     transaction.set_dirty()
...
>>> execute_bad_sql = transaction.commit_on_success(execute_bad_sql)
>>> execute_bad_sql()
Traceback (most recent call last):
    ...
IntegrityError: null value in column "email" violates not-null constraint
<BLANKLINE>

>>> transaction.rollback()

"""
