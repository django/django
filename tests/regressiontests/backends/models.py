from django.db import models
from django.db import connection

class Square(models.Model):
    root = models.IntegerField()
    square = models.PositiveIntegerField()

    def __unicode__(self):
        return "%s ** 2 == %s" % (self.root, self.square)

class Person(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)

    def __unicode__(self):
        return u'%s %s' % (self.first_name, self.last_name)

class SchoolClass(models.Model):
    year = models.PositiveIntegerField()
    day = models.CharField(max_length=9, blank=True)
    last_updated = models.DateTimeField()

qn = connection.ops.quote_name

__test__ = {'API_TESTS': """

#4896: Test cursor.executemany
>>> from django.db import connection
>>> cursor = connection.cursor()
>>> opts = Square._meta
>>> f1, f2 = opts.get_field('root'), opts.get_field('square')
>>> query = ('INSERT INTO %s (%s, %s) VALUES (%%s, %%s)'
...         % (connection.introspection.table_name_converter(opts.db_table), qn(f1.column), qn(f2.column)))
>>> cursor.executemany(query, [(i, i**2) for i in range(-5, 6)]) and None or None
>>> Square.objects.order_by('root')
[<Square: -5 ** 2 == 25>, <Square: -4 ** 2 == 16>, <Square: -3 ** 2 == 9>, <Square: -2 ** 2 == 4>, <Square: -1 ** 2 == 1>, <Square: 0 ** 2 == 0>, <Square: 1 ** 2 == 1>, <Square: 2 ** 2 == 4>, <Square: 3 ** 2 == 9>, <Square: 4 ** 2 == 16>, <Square: 5 ** 2 == 25>]

#4765: executemany with params=[] does nothing
>>> cursor.executemany(query, []) and None or None
>>> Square.objects.count()
11

#6254: fetchone, fetchmany, fetchall return strings as unicode objects
>>> Person(first_name="John", last_name="Doe").save()
>>> Person(first_name="Jane", last_name="Doe").save()
>>> Person(first_name="Mary", last_name="Agnelline").save()
>>> Person(first_name="Peter", last_name="Parker").save()
>>> Person(first_name="Clark", last_name="Kent").save()
>>> opts2 = Person._meta
>>> f3, f4 = opts2.get_field('first_name'), opts2.get_field('last_name')
>>> query2 = ('SELECT %s, %s FROM %s ORDER BY %s'
...          % (qn(f3.column), qn(f4.column), connection.introspection.table_name_converter(opts2.db_table),
...             qn(f3.column)))
>>> cursor.execute(query2) and None or None
>>> cursor.fetchone()
(u'Clark', u'Kent')

>>> list(cursor.fetchmany(2))
[(u'Jane', u'Doe'), (u'John', u'Doe')]

>>> list(cursor.fetchall())
[(u'Mary', u'Agnelline'), (u'Peter', u'Parker')]

"""}
