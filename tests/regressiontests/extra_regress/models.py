import copy

from django.contrib.auth.models import User
from django.db import models
from django.db.models.query import Q
from django.utils.datastructures import SortedDict


class RevisionableModel(models.Model):
    base = models.ForeignKey('self', null=True)
    title = models.CharField(blank=True, max_length=255)

    def __unicode__(self):
        return u"%s (%s, %s)" % (self.title, self.id, self.base.id)

    def save(self, force_insert=False, force_update=False):
        super(RevisionableModel, self).save(force_insert, force_update)
        if not self.base:
            self.base = self
            super(RevisionableModel, self).save()

    def new_revision(self):
        new_revision = copy.copy(self)
        new_revision.pk = None
        return new_revision

class Order(models.Model):
    created_by = models.ForeignKey(User)
    text = models.TextField()

__test__ = {"API_TESTS": """
# Regression tests for #7314 and #7372

>>> rm = RevisionableModel.objects.create(title='First Revision')
>>> rm.pk, rm.base.pk
(1, 1)

>>> rm2 = rm.new_revision()
>>> rm2.title = "Second Revision"
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
>>> User.objects.extra(select={'extra_field': 1}).distinct()
[<User: fred>]
>>> User.objects.extra(select={'extra_field': 1}, order_by=['extra_field'])
[<User: fred>]
>>> User.objects.extra(select={'extra_field': 1}, order_by=['extra_field']).distinct()
[<User: fred>]

"""}
