from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def _create_user(self, username, **extra_fields):
        user = self.model(username=username, **extra_fields)
        user.save(using=self._db)
        return user

    def create_superuser(self, username=None, **extra_fields):
        return self._create_user(username, **extra_fields)


class NoPasswordUser(AbstractBaseUser):
    password = None
    last_login = None
    username = models.CharField(max_length=50, unique=True)

    USERNAME_FIELD = "username"
    objects = UserManager()
