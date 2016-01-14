"""
The CustomPermissionsUser users email as the identifier, but uses the normal
Django permissions model. This allows us to check that the PermissionsMixin
includes everything that is needed to interact with the ModelBackend.
"""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.tests.custom_user import (
    CustomUserManager, RemoveGroupsAndPermissions,
)
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


class CustomPermissionsUserManager(CustomUserManager):
    def create_superuser(self, email, password, date_of_birth):
        u = self.create_user(email, password=password, date_of_birth=date_of_birth)
        u.is_superuser = True
        u.save(using=self._db)
        return u


with RemoveGroupsAndPermissions():
    @python_2_unicode_compatible
    class CustomPermissionsUser(AbstractBaseUser, PermissionsMixin):
        email = models.EmailField(verbose_name='email address', max_length=255, unique=True)
        date_of_birth = models.DateField()

        custom_objects = CustomPermissionsUserManager()

        USERNAME_FIELD = 'email'
        REQUIRED_FIELDS = ['date_of_birth']

        def get_full_name(self):
            return self.email

        def get_short_name(self):
            return self.email

        def __str__(self):
            return self.email
