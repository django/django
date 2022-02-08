from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class CustomUser(AbstractBaseUser):
    email = models.EmailField(verbose_name="email address", max_length=255, unique=True)
    custom_objects = BaseUserManager()

    USERNAME_FIELD = "email"

    class Meta:
        app_label = "test_client_regress"
