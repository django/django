from django.db import models
from django.db import connection

class Square(models.Model):
    root = models.IntegerField()
    square = models.PositiveIntegerField()

    def __unicode__(self):
        return "%s ** 2 == %s" % (self.root, self.square)

if connection.features.uses_case_insensitive_names:
    t_convert = lambda x: x.upper()
else:
    t_convert = lambda x: x
qn = connection.ops.quote_name

__test__ = {'API_TESTS': """

#4896: Test cursor.executemany
>>> from django.db import connection
>>> cursor = connection.cursor()
>>> opts = Square._meta
>>> f1, f2 = opts.get_field('root'), opts.get_field('square')
>>> query = ('INSERT INTO %s (%s, %s) VALUES (%%s, %%s)'
...         % (t_convert(opts.db_table), qn(f1.column), qn(f2.column)))
>>> cursor.executemany(query, [(i, i**2) for i in range(-5, 6)]) and None or None
>>> Square.objects.order_by('root')
[<Square: -5 ** 2 == 25>, <Square: -4 ** 2 == 16>, <Square: -3 ** 2 == 9>, <Square: -2 ** 2 == 4>, <Square: -1 ** 2 == 1>, <Square: 0 ** 2 == 0>, <Square: 1 ** 2 == 1>, <Square: 2 ** 2 == 4>, <Square: 3 ** 2 == 9>, <Square: 4 ** 2 == 16>, <Square: 5 ** 2 == 25>]

#4765: executemany with params=[] does nothing
>>> cursor.executemany(query, []) and None or None
>>> Square.objects.count()
11

"""}
