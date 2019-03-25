``sqlparse`` is a non-validating SQL parser module.
It provides support for parsing, splitting and formatting SQL statements.

Visit the `project page <https://github.com/andialbrecht/sqlparse>`_ for
additional information and documentation.

**Example Usage**


Splitting SQL statements::

   >>> import sqlparse
   >>> sqlparse.split('select * from foo; select * from bar;')
   [u'select * from foo; ', u'select * from bar;']


Formatting statemtents::

   >>> sql = 'select * from foo where id in (select id from bar);'
   >>> print sqlparse.format(sql, reindent=True, keyword_case='upper')
   SELECT *
   FROM foo
   WHERE id IN
     (SELECT id
      FROM bar);


Parsing::

   >>> sql = 'select * from someschema.mytable where id = 1'
   >>> res = sqlparse.parse(sql)
   >>> res
   (<Statement 'select...' at 0x9ad08ec>,)
   >>> stmt = res[0]
   >>> str(stmt)  # converting it back to unicode
   'select * from someschema.mytable where id = 1'
   >>> # This is how the internal representation looks like:
   >>> stmt.tokens
   (<DML 'select' at 0x9b63c34>,
    <Whitespace ' ' at 0x9b63e8c>,
    <Operator '*' at 0x9b63e64>,
    <Whitespace ' ' at 0x9b63c5c>,
    <Keyword 'from' at 0x9b63c84>,
    <Whitespace ' ' at 0x9b63cd4>,
    <Identifier 'somes...' at 0x9b5c62c>,
    <Whitespace ' ' at 0x9b63f04>,
    <Where 'where ...' at 0x9b5caac>)



