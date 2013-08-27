from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=250)
    is_published = models.BooleanField(default=False)

class BlogPost(models.Model):
    title = models.CharField(max_length=250)
    is_published = models.BooleanField(default=False)
