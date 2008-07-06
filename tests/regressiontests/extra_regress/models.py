import copy

from django.db import models
from django.db.models.query import Q


class RevisionableModel(models.Model):
    base = models.ForeignKey('self', null=True)
    title = models.CharField(blank=True, max_length=255)

    def __unicode__(self):
        return u"%s (%s, %s)" % (self.title, self.id, self.base.id)

    def save(self):
        super(RevisionableModel, self).save()
        if not self.base:
            self.base = self
            super(RevisionableModel, self).save()

    def new_revision(self):
        new_revision = copy.copy(self)
        new_revision.pk = None
        return new_revision

__test__ = {"API_TESTS": """
### Regression tests for #7314 and #7372

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

"""}
