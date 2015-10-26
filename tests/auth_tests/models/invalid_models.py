from django.contrib.auth.models import AbstractBaseUser, UserManager
from django.db import models


class CustomUserNonUniqueUsername(AbstractBaseUser):
    """
    A user with a non-unique username.

    This model is not invalid if it is used with a custom authentication
    backend which supports non-unique usernames.
    """
    username = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = UserManager()


class CustomUserNonListRequiredFields(AbstractBaseUser):
    "A user with a non-list REQUIRED_FIELDS"
    username = models.CharField(max_length=30, unique=True)
    date_of_birth = models.DateField()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = 'date_of_birth'


class CustomUserBadRequiredFields(AbstractBaseUser):
    "A user with a USERNAME_FIELD that appears in REQUIRED_FIELDS (invalid)"
    username = models.CharField(max_length=30, unique=True)
    date_of_birth = models.DateField()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['username', 'date_of_birth']
