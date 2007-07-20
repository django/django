from django.db import models

# If ticket #1578 ever slips back in, these models will not be able to be
# created (the field names being lower-cased versions of their opposite
# classes is important here).

class First(models.Model):
    second = models.IntegerField()

class Second(models.Model):
    first = models.ForeignKey(First, related_name = 'the_first')

# Protect against repetition of #1839, #2415 and #2536.
class Third(models.Model):
    name = models.CharField(maxlength=20)
    third = models.ForeignKey('self', null=True, related_name='child_set')

class Parent(models.Model):
    name = models.CharField(maxlength=20)
    bestchild = models.ForeignKey('Child', null=True, related_name='favored_by')

class Child(models.Model):
    name = models.CharField(maxlength=20)
    parent = models.ForeignKey(Parent)


__test__ = {'API_TESTS':"""
>>> Third.AddManipulator().save(dict(id='3', name='An example', another=None)) 
<Third: Third object>
>>> parent = Parent(name = 'fred')
>>> parent.save()
>>> Child.AddManipulator().save(dict(name='bam-bam', parent=parent.id))
<Child: Child object>
"""}
