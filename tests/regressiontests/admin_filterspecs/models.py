from django.db import models
from django.contrib.auth.models import User

class Book(models.Model):
    title = models.CharField(max_length=25)
    year = models.PositiveIntegerField(null=True, blank=True)
    author = models.ForeignKey(User, related_name='books_authored', blank=True, null=True)
    contributors = models.ManyToManyField(User, related_name='books_contributed', blank=True, null=True)

    def __unicode__(self):
        return self.title
