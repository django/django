from django.db import models
from django.contrib.auth.models import User

class Person(models.Model):
    name = models.CharField(maxlength=20)

class Article(models.Model):
    name = models.CharField(maxlength=100)
    body = models.TextField()
    creator = models.ForeignKey(User)
