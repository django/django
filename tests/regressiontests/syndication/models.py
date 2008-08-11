from django.db import models

class Entry(models.Model):
    title = models.CharField(max_length=200)
    date = models.DateTimeField()
    
    def __unicode__(self):
        return self.title