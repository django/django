from django.contrib.auth.models import User
from django.db import models


# This is an example of a model
# that imports a class that has an abstract base class (#13368).
class UserProfile(models.Model):
    user = models.OneToOneField(User, models.CASCADE, primary_key=True)
