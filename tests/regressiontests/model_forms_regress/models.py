import os
from django.db import models
from django import forms

class Triple(models.Model):
    left = models.IntegerField()
    middle = models.IntegerField()
    right = models.IntegerField()

    def __unicode__(self):
        return u"%d, %d, %d" % (self.left, self.middle, self.right)

    class Meta:
        unique_together = (('left', 'middle'), ('middle', 'right'))

class FilePathModel(models.Model):
    path = models.FilePathField(path=os.path.dirname(__file__), match=".*\.py$", blank=True)

__test__ = {'API_TESTS': """
When the same field is involved in multiple unique_together constraints, we
need to make sure we don't remove the data for it before doing all the
validation checking (not just failing after the first one).

>>> _ = Triple.objects.create(left=1, middle=2, right=3)
>>> class TripleForm(forms.ModelForm):
...     class Meta:
...         model = Triple

>>> form = TripleForm({'left': '1', 'middle': '2', 'right': '3'})
>>> form.is_valid()
False
>>> form = TripleForm({'left': '1', 'middle': '3', 'right': '1'})
>>> form.is_valid()
True

# Regression test for #8842: FilePathField(blank=True)
>>> class FPForm(forms.ModelForm):
...     class Meta:
...         model = FilePathModel

>>> form = FPForm()
>>> [c[1] for c in form['path'].field.choices]
['---------', '__init__.py', 'models.py']
"""}

