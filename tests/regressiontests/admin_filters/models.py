from django.db import models
from django.contrib.auth.models import User

class Book(models.Model):
    title = models.CharField(max_length=50)
    year = models.PositiveIntegerField(null=True, blank=True)
    author = models.ForeignKey(User, related_name='books_authored', blank=True, null=True)
    contributors = models.ManyToManyField(User, related_name='books_contributed', blank=True, null=True)
    is_best_seller = models.NullBooleanField(default=0)
    date_registered = models.DateField(null=True)

    def __unicode__(self):
        return self.title
