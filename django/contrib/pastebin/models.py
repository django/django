from django.db import models


# Create your models here.
class Paste(models.Model):
    key = models.CharField(max_length=16)
    code = models.TextField()
    date = models.DateTimeField(auto_now=True)
