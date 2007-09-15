from django.db import models

class Square(models.Model):
    root = models.IntegerField()
    square = models.PositiveIntegerField()

    def __unicode__(self):
        return "%s ** 2 == %s" % (self.root, self.square)

__test__ = {'API_TESTS': """

#4896: Test cursor.executemany
>>> from django.db import connection
>>> cursor = connection.cursor()
>>> cursor.executemany('INSERT INTO BACKENDS_SQUARE (ROOT, SQUARE) VALUES (%s, %s)',
...                    [(i, i**2) for i in range(-5, 6)]) and None or None
>>> Square.objects.order_by('root')
[<Square: -5 ** 2 == 25>, <Square: -4 ** 2 == 16>, <Square: -3 ** 2 == 9>, <Square: -2 ** 2 == 4>, <Square: -1 ** 2 == 1>, <Square: 0 ** 2 == 0>, <Square: 1 ** 2 == 1>, <Square: 2 ** 2 == 4>, <Square: 3 ** 2 == 9>, <Square: 4 ** 2 == 16>, <Square: 5 ** 2 == 25>]

#4765: executemany with params=[] does nothing
>>> cursor.executemany('INSERT INTO BACKENDS_SQUARE (ROOT, SQUARE) VALUES (%s, %s)', []) and None or None
>>> Square.objects.count()
11

"""}
