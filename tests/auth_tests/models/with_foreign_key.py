from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Group
from django.db import models


class Email(models.Model):
    email = models.EmailField(verbose_name='email address', max_length=255, unique=True)

    class Meta:
        app_label = 'auth'


class CustomUserWithFKManager(BaseUserManager):
    def create_superuser(self, username, email, group, password):
        user = self.model(username_id=username, email_id=email, group_id=group)
        user.set_password(password)
        user.save(using=self._db)
        return user


class CustomUserWithFK(AbstractBaseUser):
    username = models.ForeignKey(Email, related_name='primary')
    email = models.ForeignKey(Email, to_field='email', related_name='secondary')
    group = models.ForeignKey(Group)

    custom_objects = CustomUserWithFKManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'group']

    class Meta:
        app_label = 'auth'
