from django.db import models


class Artist(models.Model):
    id = models.NativeAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    good = models.BooleanField()
    
    def __unicode__(self):
        return self.name
