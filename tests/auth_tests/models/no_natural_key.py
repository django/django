from django.contrib.auth.hashers import make_password
from django.db import models


class CustomUserNoNaturalKeyManager(models.Manager):
    def create_superuser(self, email, password=None, **extra_fields):
        user = self.model(email=email, is_superuser=True, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user


class CustomUserNoNaturalKey(models.Model):
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=128)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserNoNaturalKeyManager()
