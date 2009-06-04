from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)
    published = models.DateField()

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ('title',)
