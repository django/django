from django.db import models

class Person(models.Model):
    name = models.CharField(maxlength=20)
