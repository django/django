from django.db import models

class User(models.Model):
    username = models.CharField(max_length=12, unique=True)
    serial = models.IntegerField()

class UserSite(models.Model):
    user = models.ForeignKey(User, to_field="username")
    data = models.IntegerField()
