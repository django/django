from django.contrib.auth.models import User
from django.db import models


# Regression for #13368. This is an example of a model
# that imports a class that has an abstract base class.
class UserProfile(models.Model):
    user = models.OneToOneField(User, primary_key=True)
