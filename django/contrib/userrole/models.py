from django.contrib.auth.models import Group, Permission, User
from django.db import models
from django.utils.translation import ugettext_lazy as _


# Create your models here.


class UserRole(models.Model):
    '''
    UserRole provides role based access control for django. It helps to decouple User management and permission management,
    which is desirable for enterprises with more than 500 employees.
    A User can be assigned to zero-to-many UserRoles and a UserRole can have zero-to-many users
    '''

    name = models.CharField(max_length=128, unique=True, help_text=_("role's name, be globally unique"))
    users = models.ManyToManyField(User, related_name='users', help_text=_('users assigned to this role'), blank=True)
    admins = models.ManyToManyField(User, related_name='admins', help_text=_(
        'admins of this role, who can add users to and remove users from this role'), blank=True)
    permissions = models.ManyToManyField(Permission, help_text=_('permissions assigned to this role'), blank=True)
    groups = models.ManyToManyField(Group, help_text=_('groups assigned to this role'), blank=True)

    def __unicode__(self):
        return self.name
