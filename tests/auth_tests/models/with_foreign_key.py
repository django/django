from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, Group, User,
)
from django.db import models


class Email(models.Model):
    email = models.EmailField(verbose_name='email address', max_length=255, unique=True)


class CustomUserWithFKManager(BaseUserManager):
    def create_superuser(self, username, email, group, password):
        user = self.model(username=username, email=email, group=group)
        user.set_password(password)
        user.save(using=self._db)
        return user


class CustomUserWithFK(AbstractBaseUser):
    username = models.ForeignKey(Email, models.CASCADE, related_name='primary')
    email = models.ForeignKey(Email, models.CASCADE, to_field='email', related_name='secondary')
    group = models.ForeignKey(Group, models.CASCADE)

    custom_objects = CustomUserWithFKManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'group']


class Company(models.Model):
    title = models.CharField(max_length=128)


class DefaultUserWithFK(User):
    company = models.ForeignKey(Company, models.CASCADE)

    REQUIRED_FIELDS = ['email', 'company']
