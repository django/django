from django.db import models
from django.contrib.auth.models import User


# Regression for #13368. This is an example of a model
# that imports a class that has an abstract base class.
class UserProfile(models.Model):
    user = models.OneToOneField(User, primary_key=True)
