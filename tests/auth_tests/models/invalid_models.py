from django.contrib.auth.models import AbstractBaseUser
from django.db import models


class CustomUserNonUniqueUsername(AbstractBaseUser):
    "A user with a non-unique username"
    username = models.CharField(max_length=30)

    USERNAME_FIELD = 'username'

    class Meta:
        app_label = 'auth'


class CustomUserNonListRequiredFields(AbstractBaseUser):
    "A user with a non-list REQUIRED_FIELDS"
    username = models.CharField(max_length=30, unique=True)
    date_of_birth = models.DateField()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = 'date_of_birth'

    class Meta:
        app_label = 'auth'


class CustomUserBadRequiredFields(AbstractBaseUser):
    "A user with a USERNAME_FIELD that appears in REQUIRED_FIELDS (invalid)"
    username = models.CharField(max_length=30, unique=True)
    date_of_birth = models.DateField()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['username', 'date_of_birth']

    class Meta:
        app_label = 'auth'
