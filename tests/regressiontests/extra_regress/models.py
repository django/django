import datetime

import django.utils.copycompat as copy

from django.contrib.auth.models import User
from django.db import models
from django.db.models.query import Q
from django.utils.datastructures import SortedDict


class RevisionableModel(models.Model):
    base = models.ForeignKey('self', null=True)
    title = models.CharField(blank=True, max_length=255)
    when = models.DateTimeField(default=datetime.datetime.now)

    def __unicode__(self):
        return u"%s (%s, %s)" % (self.title, self.id, self.base.id)

    def save(self, *args, **kwargs):
        super(RevisionableModel, self).save(*args, **kwargs)
        if not self.base:
            self.base = self
            kwargs.pop('force_insert', None)
            kwargs.pop('force_update', None)
            super(RevisionableModel, self).save(*args, **kwargs)

    def new_revision(self):
        new_revision = copy.copy(self)
        new_revision.pk = None
        return new_revision

class Order(models.Model):
    created_by = models.ForeignKey(User)
    text = models.TextField()

class TestObject(models.Model):
    first = models.CharField(max_length=20)
    second = models.CharField(max_length=20)
    third = models.CharField(max_length=20)

    def __unicode__(self):
        return u'TestObject: %s,%s,%s' % (self.first,self.second,self.third)

__test__ = {"API_TESTS": """
# Regression tests for #7314 and #7372

>>> rm = RevisionableModel.objects.create(title='First Revision', when=datetime.datetime(2008, 9, 28, 10, 30, 0))
>>> rm.pk, rm.base.pk
(1, 1)

>>> rm2 = rm.new_revision()
>>> rm2.title = "Second Revision"
>>> rm.when = datetime.datetime(2008, 9, 28, 14, 25, 0)
>>> rm2.save()
>>> print u"%s of %s" % (rm2.title, rm2.base.title)
Second Revision of First Revision

>>> rm2.pk, rm2.base.pk
(2, 1)

Queryset to match most recent revision:
>>> qs = RevisionableModel.objects.extra(where=["%(table)s.id IN (SELECT MAX(rev.id) FROM %(table)s rev GROUP BY rev.base_id)" % {'table': RevisionableModel._meta.db_table,}],)
>>> qs
[<RevisionableModel: Second Revision (2, 1)>]

Queryset to search for string in title:
>>> qs2 = RevisionableModel.objects.filter(title__contains="Revision")
>>> qs2
[<RevisionableModel: First Revision (1, 1)>, <RevisionableModel: Second Revision (2, 1)>]

Following queryset should return the most recent revision:
>>> qs & qs2
[<RevisionableModel: Second Revision (2, 1)>]

>>> u = User.objects.create_user(username="fred", password="secret", email="fred@example.com")

# General regression tests: extra select parameters should stay tied to their
# corresponding select portions. Applies when portions are updated or otherwise
# moved around.
>>> qs = User.objects.extra(select=SortedDict((("alpha", "%s"), ("beta", "2"), ("gamma", "%s"))), select_params=(1, 3))
>>> qs = qs.extra(select={"beta": 4})
>>> qs = qs.extra(select={"alpha": "%s"}, select_params=[5])
>>> result = {'alpha': 5, 'beta': 4, 'gamma': 3}
>>> list(qs.filter(id=u.id).values('alpha', 'beta', 'gamma')) == [result]
True

# Regression test for #7957: Combining extra() calls should leave the
# corresponding parameters associated with the right extra() bit. I.e. internal
# dictionary must remain sorted.
>>> User.objects.extra(select={"alpha": "%s"}, select_params=(1,)).extra(select={"beta": "%s"}, select_params=(2,))[0].alpha
1
>>> User.objects.extra(select={"beta": "%s"}, select_params=(1,)).extra(select={"alpha": "%s"}, select_params=(2,))[0].alpha
2

# Regression test for #7961: When not using a portion of an extra(...) in a
# query, remove any corresponding parameters from the query as well.
>>> list(User.objects.extra(select={"alpha": "%s"}, select_params=(-6,)).filter(id=u.id).values_list('id', flat=True)) == [u.id]
True

# Regression test for #8063: limiting a query shouldn't discard any extra()
# bits.
>>> qs = User.objects.all().extra(where=['id=%s'], params=[u.id])
>>> qs
[<User: fred>]
>>> qs[:1]
[<User: fred>]

# Regression test for #8039: Ordering sometimes removed relevant tables from
# extra(). This test is the critical case: ordering uses a table, but then
# removes the reference because of an optimisation. The table should still be
# present because of the extra() call.
>>> Order.objects.extra(where=["username=%s"], params=["fred"], tables=["auth_user"]).order_by('created_by')
[]

# Regression test for #8819: Fields in the extra(select=...) list should be
# available to extra(order_by=...).
>>> User.objects.filter(pk=u.id).extra(select={'extra_field': 1}).distinct()
[<User: fred>]
>>> User.objects.filter(pk=u.id).extra(select={'extra_field': 1}, order_by=['extra_field'])
[<User: fred>]
>>> User.objects.filter(pk=u.id).extra(select={'extra_field': 1}, order_by=['extra_field']).distinct()
[<User: fred>]

# When calling the dates() method on a queryset with extra selection columns,
# we can (and should) ignore those columns. They don't change the result and
# cause incorrect SQL to be produced otherwise.
>>> RevisionableModel.objects.extra(select={"the_answer": 'id'}).dates('when', 'month')
[datetime.datetime(2008, 9, 1, 0, 0)]

# Regression test for #10256... If there is a values() clause, Extra columns are
# only returned if they are explicitly mentioned.
>>> TestObject(first='first', second='second', third='third').save()

>>> TestObject.objects.extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third')))).values()
[{'bar': u'second', 'third': u'third', 'second': u'second', 'whiz': u'third', 'foo': u'first', 'id': 1, 'first': u'first'}]

# Extra clauses after an empty values clause are still included
>>> TestObject.objects.values().extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third'))))
[{'bar': u'second', 'third': u'third', 'second': u'second', 'whiz': u'third', 'foo': u'first', 'id': 1, 'first': u'first'}]

# Extra columns are ignored if not mentioned in the values() clause
>>> TestObject.objects.extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third')))).values('first', 'second')
[{'second': u'second', 'first': u'first'}]

# Extra columns after a non-empty values() clause are ignored
>>> TestObject.objects.values('first', 'second').extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third'))))
[{'second': u'second', 'first': u'first'}]

# Extra columns can be partially returned
>>> TestObject.objects.extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third')))).values('first', 'second', 'foo')
[{'second': u'second', 'foo': u'first', 'first': u'first'}]

# Also works if only extra columns are included
>>> TestObject.objects.extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third')))).values('foo', 'whiz')
[{'foo': u'first', 'whiz': u'third'}]

# Values list works the same way
# All columns are returned for an empty values_list()
>>> TestObject.objects.extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third')))).values_list()
[(u'first', u'second', u'third', 1, u'first', u'second', u'third')]

# Extra columns after an empty values_list() are still included
>>> TestObject.objects.values_list().extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third'))))
[(u'first', u'second', u'third', 1, u'first', u'second', u'third')]

# Extra columns ignored completely if not mentioned in values_list()
>>> TestObject.objects.extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third')))).values_list('first', 'second')
[(u'first', u'second')]

# Extra columns after a non-empty values_list() clause are ignored completely
>>> TestObject.objects.values_list('first', 'second').extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third'))))
[(u'first', u'second')]

>>> TestObject.objects.extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third')))).values_list('second', flat=True)
[u'second']

# Only the extra columns specified in the values_list() are returned
>>> TestObject.objects.extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third')))).values_list('first', 'second', 'whiz')
[(u'first', u'second', u'third')]

# ...also works if only extra columns are included
>>> TestObject.objects.extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third')))).values_list('foo','whiz')
[(u'first', u'third')]

>>> TestObject.objects.extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third')))).values_list('whiz', flat=True)
[u'third']

# ... and values are returned in the order they are specified
>>> TestObject.objects.extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third')))).values_list('whiz','foo')
[(u'third', u'first')]

>>> TestObject.objects.extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third')))).values_list('first','id')
[(u'first', 1)]

>>> TestObject.objects.extra(select=SortedDict((('foo','first'),('bar','second'),('whiz','third')))).values_list('whiz', 'first', 'bar', 'id')
[(u'third', u'first', u'second', 1)]

# Regression for #10847: the list of extra columns can always be accurately evaluated.
# Using an inner query ensures that as_sql() is producing correct output
# without requiring full evaluation and execution of the inner query.
>>> TestObject.objects.extra(select={'extra': 1}).values('pk')
[{'pk': 1}]

>>> TestObject.objects.filter(pk__in=TestObject.objects.extra(select={'extra': 1}).values('pk'))
[<TestObject: TestObject: first,second,third>]

>>> TestObject.objects.values('pk').extra(select={'extra': 1})
[{'pk': 1}]

>>> TestObject.objects.filter(pk__in=TestObject.objects.values('pk').extra(select={'extra': 1}))
[<TestObject: TestObject: first,second,third>]

"""}
