"""
27. Many-to-many and many-to-one relationships to the same table.

This is a response to bug #1535

"""

from django.db import models

class User(models.Model):
    username = models.CharField(maxlength=20)

class Issue(models.Model):
    num = models.IntegerField()
    cc = models.ManyToManyField(User, blank=True, related_name='test_issue_cc')
    client = models.ForeignKey(User, related_name='test_issue_client')
    def __repr__(self):
        return "<Issue %d>" % (self.num,)
        
    class Meta:
        ordering = ('num',)


API_TESTS = """
>>> Issue.objects.all()
[]
>>> r = User(username='russell')
>>> r.save()
>>> g = User(username='gustav')
>>> g.save()
>>> i = Issue(num=1)
>>> i.client = r
>>> i.validate()
{}
>>> i.save()
>>> i2 = Issue(num=2)
>>> i2.client = r
>>> i2.validate()
{}
>>> i2.save()
>>> i2.cc.add(r)
>>> i3 = Issue(num=3)
>>> i3.client = g
>>> i3.validate()
{}
>>> i3.save()
>>> i3.cc.add(r)
>>> from django.db.models.query import Q
>>> Issue.objects.filter(client=r.id)
[<Issue 1>, <Issue 2>]
>>> Issue.objects.filter(client=g.id)
[<Issue 3>]
>>> Issue.objects.filter(cc__id__exact=g.id)
[]
>>> Issue.objects.filter(cc__id__exact=r.id)
[<Issue 2>, <Issue 3>]

# Queries that combine results from the m2m and the m2o relationship.
# 3 ways of saying the same thing:
>>> Issue.objects.filter(Q(cc__id__exact=r.id) | Q(client=r.id))
[<Issue 1>, <Issue 2>, <Issue 3>]
>>> Issue.objects.filter(cc__id__exact=r.id) | Issue.objects.filter(client=r.id)
[<Issue 1>, <Issue 2>, <Issue 3>]
>>> Issue.objects.filter(Q(client=r.id) | Q(cc__id__exact=r.id))
[<Issue 1>, <Issue 2>, <Issue 3>]
"""
