"""
28. Many-to-many and many-to-one relationships to the same table

Make sure to set ``related_name`` if you use relationships to the same table.
"""

from django.db import models

class User(models.Model):
    username = models.CharField(maxlength=20)

class Issue(models.Model):
    num = models.IntegerField()
    cc = models.ManyToManyField(User, blank=True, related_name='test_issue_cc')
    client = models.ForeignKey(User, related_name='test_issue_client')

    def __str__(self):
        return str(self.num)

    class Meta:
        ordering = ('num',)


__test__ = {'API_TESTS':"""
>>> Issue.objects.all()
[]
>>> r = User(username='russell')
>>> r.save()
>>> g = User(username='gustav')
>>> g.save()

>>> i = Issue(num=1)
>>> i.client = r
>>> i.save()

>>> i2 = Issue(num=2)
>>> i2.client = r
>>> i2.save()
>>> i2.cc.add(r)

>>> i3 = Issue(num=3)
>>> i3.client = g
>>> i3.save()
>>> i3.cc.add(r)

>>> from django.db.models.query import Q

>>> Issue.objects.filter(client=r.id)
[<Issue: 1>, <Issue: 2>]
>>> Issue.objects.filter(client=g.id)
[<Issue: 3>]
>>> Issue.objects.filter(cc__id__exact=g.id)
[]
>>> Issue.objects.filter(cc__id__exact=r.id)
[<Issue: 2>, <Issue: 3>]

# These queries combine results from the m2m and the m2o relationships.
# They're three ways of saying the same thing.
>>> Issue.objects.filter(Q(cc__id__exact=r.id) | Q(client=r.id))
[<Issue: 1>, <Issue: 2>, <Issue: 3>]
>>> Issue.objects.filter(cc__id__exact=r.id) | Issue.objects.filter(client=r.id)
[<Issue: 1>, <Issue: 2>, <Issue: 3>]
>>> Issue.objects.filter(Q(client=r.id) | Q(cc__id__exact=r.id))
[<Issue: 1>, <Issue: 2>, <Issue: 3>]
"""}
