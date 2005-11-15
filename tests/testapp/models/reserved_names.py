"""
18. Using SQL reserved names

Need to use a reserved SQL name as a column name or table name? Need to include
a hyphen in a column or table name? No problem. Django quotes names
appropriately behind the scenes, so your database won't complain about
reserved-name usage.
"""

from django.core import meta

class Thing(meta.Model):
    when = meta.CharField(maxlength=1, primary_key=True)
    join = meta.CharField(maxlength=1)
    like = meta.CharField(maxlength=1)
    drop = meta.CharField(maxlength=1)
    alter = meta.CharField(maxlength=1)
    having = meta.CharField(maxlength=1)
    where = meta.CharField(maxlength=1)
    has_hyphen = meta.CharField(maxlength=1, db_column='has-hyphen')
    class META:
       db_table = 'select'

    def __repr__(self):
        return self.when

API_TESTS = """
>>> t = things.Thing(when='a', join='b', like='c', drop='d', alter='e', having='f', where='g', has_hyphen='h')
>>> t.save()
>>> print t.when
a

>>> u = things.Thing(when='h', join='i', like='j', drop='k', alter='l', having='m', where='n')
>>> u.save()
>>> print u.when
h

>>> things.get_list(order_by=['when'])
[a, h]
>>> v = things.get_object(pk='a')
>>> print v.join
b
>>> print v.where
g
>>> things.get_list(order_by=['select.when'])
[a, h]
"""
