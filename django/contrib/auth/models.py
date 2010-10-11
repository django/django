import datetime
import urllib

from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.manager import EmptyManager
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import smart_str
from django.utils.hashcompat import md5_constructor, sha_constructor
from django.utils.translation import ugettext_lazy as _


UNUSABLE_PASSWORD = '!' # This will never be a valid hash

def get_hexdigest(algorithm, salt, raw_password):
    """
    Returns a string of the hexdigest of the given plaintext password and salt
    using the given algorithm ('md5', 'sha1' or 'crypt').
    """
    raw_password, salt = smart_str(raw_password), smart_str(salt)
    if algorithm == 'crypt':
        try:
            import crypt
        except ImportError:
            raise ValueError('"crypt" password algorithm not supported in this environment')
        return crypt.crypt(raw_password, salt)

    if algorithm == 'md5':
        return md5_constructor(salt + raw_password).hexdigest()
    elif algorithm == 'sha1':
        return sha_constructor(salt + raw_password).hexdigest()
    raise ValueError("Got unknown password algorithm type in password.")

def check_password(raw_password, enc_password):
    """
    Returns a boolean of whether the raw_password was correct. Handles
    encryption formats behind the scenes.
    """
    algo, salt, hsh = enc_password.split('$')
    return hsh == get_hexdigest(algo, salt, raw_password)

class SiteProfileNotAvailable(Exception):
    pass

class PermissionManager(models.Manager):
    def get_by_natural_key(self, codename, app_label, model):
        return self.get(
            codename=codename,
            content_type=ContentType.objects.get_by_natural_key(app_label, model)
        )

class Permission(models.Model):
    """The permissions system provides a way to assign permissions to specific users and groups of users.

    The permission system is used by the Django admin site, but may also be useful in your own code. The Django admin site uses permissions as follows:

        - The "add" permission limits the user's ability to view the "add" form and add an object.
        - The "change" permission limits a user's ability to view the change list, view the "change" form and change an object.
        - The "delete" permission limits the ability to delete an object.

    Permissions are set globally per type of object, not per specific object instance. It is possible to say "Mary may change news stories," but it's not currently possible to say "Mary may change news stories, but only the ones she created herself" or "Mary may only change news stories that have a certain status or publication date."

    Three basic permissions -- add, change and delete -- are automatically created for each Django model.
    """
    name = models.CharField(_('name'), max_length=50)
    content_type = models.ForeignKey(ContentType)
    codename = models.CharField(_('codename'), max_length=100)
    objects = PermissionManager()

    class Meta:
        verbose_name = _('permission')
        verbose_name_plural = _('permissions')
        unique_together = (('content_type', 'codename'),)
        ordering = ('content_type__app_label', 'content_type__model', 'codename')

    def __unicode__(self):
        return u"%s | %s | %s" % (
            unicode(self.content_type.app_label),
            unicode(self.content_type),
            unicode(self.name))

    def natural_key(self):
        return (self.codename,) + self.content_type.natural_key()
    natural_key.dependencies = ['contenttypes.contenttype']

class Group(models.Model):
    """Groups are a generic way of categorizing users to apply permissions, or some other label, to those users. A user can belong to any number of groups.

    A user in a group automatically has all the permissions granted to that group. For example, if the group Site editors has the permission can_edit_home_page, any user in that group will have that permission.

    Beyond permissions, groups are a convenient way to categorize users to apply some label, or extended functionality, to them. For example, you could create a group 'Special users', and you could write code that would do special things to those users -- such as giving them access to a members-only portion of your site, or sending them members-only e-mail messages.
    """
    name = models.CharField(_('name'), max_length=80, unique=True)
    permissions = models.ManyToManyField(Permission, verbose_name=_('permissions'), blank=True)

    class Meta:
        verbose_name = _('group')
        verbose_name_plural = _('groups')

    def __unicode__(self):
        return self.name

class UserManager(models.Manager):
    def create_user(self, username, email, password=None):
        """
        Creates and saves a User with the given username, e-mail and password.
        """
        now = datetime.datetime.now()

        # Normalize the address by lowercasing the domain part of the email
        # address.
        try:
            email_name, domain_part = email.strip().split('@', 1)
        except ValueError:
            pass
        else:
            email = '@'.join([email_name, domain_part.lower()])

        user = self.model(username=username, email=email, is_staff=False,
                         is_active=True, is_superuser=False, last_login=now,
                         date_joined=now)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password):
        u = self.create_user(username, email, password)
        u.is_staff = True
        u.is_active = True
        u.is_superuser = True
        u.save(using=self._db)
        return u

    def make_random_password(self, length=10, allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'):
        "Generates a random password with the given length and given allowed_chars"
        # Note that default value of allowed_chars does not have "I" or letters
        # that look like it -- just to avoid confusion.
        from random import choice
        return ''.join([choice(allowed_chars) for i in range(length)])


# A few helper functions for common logic between User and AnonymousUser.
def _user_get_all_permissions(user, obj):
    permissions = set()
    anon = user.is_anonymous()
    for backend in auth.get_backends():
        if not anon or backend.supports_anonymous_user:
            if hasattr(backend, "get_all_permissions"):
                if obj is not None:
                    if backend.supports_object_permissions:
                        permissions.update(
                            backend.get_all_permissions(user, obj)
                        )
                else:
                    permissions.update(backend.get_all_permissions(user))
    return permissions


def _user_has_perm(user, perm, obj):
    anon = user.is_anonymous()
    for backend in auth.get_backends():
        if not anon or backend.supports_anonymous_user:
            if hasattr(backend, "has_perm"):
                if obj is not None:
                    if (backend.supports_object_permissions and
                        backend.has_perm(user, perm, obj)):
                            return True
                else:
                    if backend.has_perm(user, perm):
                        return True
    return False


def _user_has_module_perms(user, app_label):
    anon = user.is_anonymous()
    for backend in auth.get_backends():
        if not anon or backend.supports_anonymous_user:
            if hasattr(backend, "has_module_perms"):
                if backend.has_module_perms(user, app_label):
                    return True
    return False


class User(models.Model):
    """
    Users within the Django authentication system are represented by this model.

    Username and password are required. Other fields are optional.
    """
    username = models.CharField(_('username'), max_length=30, unique=True, help_text=_("Required. 30 characters or fewer. Letters, numbers and @/./+/-/_ characters"))
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
    email = models.EmailField(_('e-mail address'), blank=True)
    password = models.CharField(_('password'), max_length=128, help_text=_("Use '[algo]$[salt]$[hexdigest]' or use the <a href=\"password/\">change password form</a>."))
    is_staff = models.BooleanField(_('staff status'), default=False, help_text=_("Designates whether the user can log into this admin site."))
    is_active = models.BooleanField(_('active'), default=True, help_text=_("Designates whether this user should be treated as active. Unselect this instead of deleting accounts."))
    is_superuser = models.BooleanField(_('superuser status'), default=False, help_text=_("Designates that this user has all permissions without explicitly assigning them."))
    last_login = models.DateTimeField(_('last login'), default=datetime.datetime.now)
    date_joined = models.DateTimeField(_('date joined'), default=datetime.datetime.now)
    groups = models.ManyToManyField(Group, verbose_name=_('groups'), blank=True,
        help_text=_("In addition to the permissions manually assigned, this user will also get all permissions granted to each group he/she is in."))
    user_permissions = models.ManyToManyField(Permission, verbose_name=_('user permissions'), blank=True)
    objects = UserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __unicode__(self):
        return self.username

    def get_absolute_url(self):
        return "/users/%s/" % urllib.quote(smart_str(self.username))

    def is_anonymous(self):
        """
        Always returns False. This is a way of comparing User objects to
        anonymous users.
        """
        return False

    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        """
        return True

    def get_full_name(self):
        "Returns the first_name plus the last_name, with a space in between."
        full_name = u'%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def set_password(self, raw_password):
        if raw_password is None:
            self.set_unusable_password()
        else:
            import random
            algo = 'sha1'
            salt = get_hexdigest(algo, str(random.random()), str(random.random()))[:5]
            hsh = get_hexdigest(algo, salt, raw_password)
            self.password = '%s$%s$%s' % (algo, salt, hsh)

    def check_password(self, raw_password):
        """
        Returns a boolean of whether the raw_password was correct. Handles
        encryption formats behind the scenes.
        """
        # Backwards-compatibility check. Older passwords won't include the
        # algorithm or salt.
        if '$' not in self.password:
            is_correct = (self.password == get_hexdigest('md5', '', raw_password))
            if is_correct:
                # Convert the password to the new, more secure format.
                self.set_password(raw_password)
                self.save()
            return is_correct
        return check_password(raw_password, self.password)

    def set_unusable_password(self):
        # Sets a value that will never be a valid hash
        self.password = UNUSABLE_PASSWORD

    def has_usable_password(self):
        if self.password is None \
            or self.password == UNUSABLE_PASSWORD:
            return False
        else:
            return True

    def get_group_permissions(self, obj=None):
        """
        Returns a list of permission strings that this user has through
        his/her groups. This method queries all available auth backends.
        If an object is passed in, only permissions matching this object
        are returned.
        """
        permissions = set()
        for backend in auth.get_backends():
            if hasattr(backend, "get_group_permissions"):
                if obj is not None:
                    if backend.supports_object_permissions:
                        permissions.update(
                            backend.get_group_permissions(self, obj)
                        )
                else:
                    permissions.update(backend.get_group_permissions(self))
        return permissions

    def get_all_permissions(self, obj=None):
        return _user_get_all_permissions(self, obj)

    def has_perm(self, perm, obj=None):
        """
        Returns True if the user has the specified permission. This method
        queries all available auth backends, but returns immediately if any
        backend returns True. Thus, a user who has permission from a single
        auth backend is assumed to have permission in general. If an object
        is provided, permissions for this specific object are checked.
        """
        # Inactive users have no permissions.
        if not self.is_active:
            return False

        # Superusers have all permissions.
        if self.is_superuser:
            return True

        # Otherwise we need to check the backends.
        return _user_has_perm(self, perm, obj)

    def has_perms(self, perm_list, obj=None):
        """
        Returns True if the user has each of the specified permissions.
        If object is passed, it checks if the user has all required perms
        for this object.
        """
        for perm in perm_list:
            if not self.has_perm(perm, obj):
                return False
        return True

    def has_module_perms(self, app_label):
        """
        Returns True if the user has any permissions in the given app
        label. Uses pretty much the same logic as has_perm, above.
        """
        if not self.is_active:
            return False

        if self.is_superuser:
            return True

        return _user_has_module_perms(self, app_label)

    def get_and_delete_messages(self):
        messages = []
        for m in self.message_set.all():
            messages.append(m.message)
            m.delete()
        return messages

    def email_user(self, subject, message, from_email=None):
        "Sends an e-mail to this User."
        from django.core.mail import send_mail
        send_mail(subject, message, from_email, [self.email])

    def get_profile(self):
        """
        Returns site-specific profile for this user. Raises
        SiteProfileNotAvailable if this site does not allow profiles.
        """
        if not hasattr(self, '_profile_cache'):
            from django.conf import settings
            if not getattr(settings, 'AUTH_PROFILE_MODULE', False):
                raise SiteProfileNotAvailable('You need to set AUTH_PROFILE_MO'
                                              'DULE in your project settings')
            try:
                app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
            except ValueError:
                raise SiteProfileNotAvailable('app_label and model_name should'
                        ' be separated by a dot in the AUTH_PROFILE_MODULE set'
                        'ting')

            try:
                model = models.get_model(app_label, model_name)
                if model is None:
                    raise SiteProfileNotAvailable('Unable to load the profile '
                        'model, check AUTH_PROFILE_MODULE in your project sett'
                        'ings')
                self._profile_cache = model._default_manager.using(self._state.db).get(user__id__exact=self.id)
                self._profile_cache.user = self
            except (ImportError, ImproperlyConfigured):
                raise SiteProfileNotAvailable
        return self._profile_cache

    def _get_message_set(self):
        import warnings
        warnings.warn('The user messaging API is deprecated. Please update'
                      ' your code to use the new messages framework.',
                      category=DeprecationWarning)
        return self._message_set
    message_set = property(_get_message_set)

class Message(models.Model):
    """
    The message system is a lightweight way to queue messages for given
    users. A message is associated with a User instance (so it is only
    applicable for registered users). There's no concept of expiration or
    timestamps. Messages are created by the Django admin after successful
    actions. For example, "The poll Foo was created successfully." is a
    message.
    """
    user = models.ForeignKey(User, related_name='_message_set')
    message = models.TextField(_('message'))

    def __unicode__(self):
        return self.message

class AnonymousUser(object):
    id = None
    username = ''
    is_staff = False
    is_active = False
    is_superuser = False
    _groups = EmptyManager()
    _user_permissions = EmptyManager()

    def __init__(self):
        pass

    def __unicode__(self):
        return 'AnonymousUser'

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return 1 # instances always return the same hash value

    def save(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def set_password(self, raw_password):
        raise NotImplementedError

    def check_password(self, raw_password):
        raise NotImplementedError

    def _get_groups(self):
        return self._groups
    groups = property(_get_groups)

    def _get_user_permissions(self):
        return self._user_permissions
    user_permissions = property(_get_user_permissions)

    def get_group_permissions(self, obj=None):
        return set()

    def get_all_permissions(self, obj=None):
        return _user_get_all_permissions(self, obj=obj)

    def has_perm(self, perm, obj=None):
        return _user_has_perm(self, perm, obj=obj)

    def has_perms(self, perm_list, obj=None):
        for perm in perm_list:
            if not self.has_perm(perm, obj):
                return False
        return True

    def has_module_perms(self, module):
        return _user_has_module_perms(self, module)

    def get_and_delete_messages(self):
        return []

    def is_anonymous(self):
        return True

    def is_authenticated(self):
        return False
