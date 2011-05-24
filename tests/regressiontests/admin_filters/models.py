from django.db import models
from django.contrib.auth.models import User

class Book(models.Model):
    title = models.CharField(max_length=50)
    year = models.PositiveIntegerField(null=True, blank=True)
    author = models.ForeignKey(User, related_name='books_authored', blank=True, null=True)
    contributors = models.ManyToManyField(User, related_name='books_contributed', blank=True, null=True)
    is_best_seller = models.NullBooleanField(default=0)
    date_registered = models.DateField(null=True)
    no = models.IntegerField(verbose_name=u'number', blank=True, null=True) # This field is intentionally 2 characters long. See #16080.

    def __unicode__(self):
        return self.title
