FAQ: Databases and models
=========================

.. _faq-see-raw-sql-queries:

How can I see the raw SQL queries Django is running?
----------------------------------------------------

Make sure your Django :setting:`DEBUG` setting is set to ``True``.
Then, just do this::

    >>> from django.db import connection
    >>> connection.queries
    [{'sql': 'SELECT polls_polls.id, polls_polls.question, polls_polls.pub_date FROM polls_polls',
    'time': '0.002'}]

``connection.queries`` is only available if :setting:`DEBUG` is ``True``.
It's a list of dictionaries in order of query execution. Each dictionary has
the following::

    ``sql`` -- The raw SQL statement
    ``time`` -- How long the statement took to execute, in seconds.

``connection.queries`` includes all SQL statements -- INSERTs, UPDATES,
SELECTs, etc. Each time your app hits the database, the query will be recorded.
Note that the SQL recorded here may be :ref:`incorrectly quoted under SQLite
<sqlite-connection-queries>`.

If you are using :doc:`multiple databases</topics/db/multi-db>`, you can use the
same interface on each member of the ``connections`` dictionary::

    >>> from django.db import connections
    >>> connections['my_db_alias'].queries

Can I use Django with a pre-existing database?
----------------------------------------------

Yes. See :doc:`Integrating with a legacy database </howto/legacy-databases>`.

If I make changes to a model, how do I update the database?
-----------------------------------------------------------

If you don't mind clearing data, your project's ``manage.py`` utility has a
:djadmin:`flush` option to reset the database to the state it was in
immediately after :djadmin:`syncdb` was executed.

If you do care about deleting data, you'll have to execute the ``ALTER TABLE``
statements manually in your database.

There are `external projects which handle schema updates
<http://www.djangopackages.com/grids/g/database-migration/>`_, of which the current
defacto standard is `south <http://south.aeracode.org/>`_.

Do Django models support multiple-column primary keys?
------------------------------------------------------

No. Only single-column primary keys are supported.

But this isn't an issue in practice, because there's nothing stopping you from
adding other constraints (using the ``unique_together`` model option or
creating the constraint directly in your database), and enforcing the
uniqueness at that level. Single-column primary keys are needed for things such
as the admin interface to work; e.g., you need a simple way of being able to
specify an object to edit or delete.

How do I add database-specific options to my CREATE TABLE statements, such as specifying MyISAM as the table type?
------------------------------------------------------------------------------------------------------------------

We try to avoid adding special cases in the Django code to accommodate all the
database-specific options such as table type, etc. If you'd like to use any of
these options, create an :ref:`SQL initial data file <initial-sql>` that
contains ``ALTER TABLE`` statements that do what you want to do. The initial
data files are executed in your database after the ``CREATE TABLE`` statements.

For example, if you're using MySQL and want your tables to use the MyISAM table
type, create an initial data file and put something like this in it::

    ALTER TABLE myapp_mytable ENGINE=MyISAM;

As explained in the :ref:`SQL initial data file <initial-sql>` documentation,
this SQL file can contain arbitrary SQL, so you can make any sorts of changes
you need to make.

Why is Django leaking memory?
-----------------------------

Django isn't known to leak memory. If you find your Django processes are
allocating more and more memory, with no sign of releasing it, check to make
sure your :setting:`DEBUG` setting is set to ``False``. If :setting:`DEBUG`
is ``True``, then Django saves a copy of every SQL statement it has executed.

(The queries are saved in ``django.db.connection.queries``. See
`How can I see the raw SQL queries Django is running?`_.)

To fix the problem, set :setting:`DEBUG` to ``False``.

If you need to clear the query list manually at any point in your functions,
just call ``reset_queries()``, like this::

    from django import db
    db.reset_queries()
