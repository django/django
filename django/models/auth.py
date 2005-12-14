from django.core import validators
from django.db import models
from django.models import core
from django.utils.translation import gettext_lazy as _

SESSION_KEY = '_auth_user_id'

class Permission(models.Model):
    name = models.CharField(_('name'), maxlength=50)
    package = models.ForeignKey(core.Package, db_column='package')
    codename = models.CharField(_('codename'), maxlength=100)
    class META:
        verbose_name = _('Permission')
        verbose_name_plural = _('Permissions')
        unique_together = (('package', 'codename'),)
        ordering = ('package', 'codename')

    def __repr__(self):
        return "%s | %s" % (self.package_id, self.name)

class Group(models.Model):
    name = models.CharField(_('name'), maxlength=80, unique=True)
    permissions = models.ManyToManyField(Permission, blank=True, filter_interface=models.HORIZONTAL)
    class META:
        verbose_name = _('Group')
        verbose_name_plural = _('Groups')
        ordering = ('name',)
        admin = models.Admin(
            search_fields = ('name',),
        )

    def __repr__(self):
        return self.name

class User(models.Model):
    username = models.CharField(_('username'), maxlength=30, unique=True, validator_list=[validators.isAlphaNumeric])
    first_name = models.CharField(_('first name'), maxlength=30, blank=True)
    last_name = models.CharField(_('last name'), maxlength=30, blank=True)
    email = models.EmailField(_('e-mail address'), blank=True)
    password = models.CharField(_('password'), maxlength=128, help_text=_("Use '[algo]$[salt]$[hexdigest]'"))
    is_staff = models.BooleanField(_('staff status'), help_text=_("Designates whether the user can log into this admin site."))
    is_active = models.BooleanField(_('active'), default=True)
    is_superuser = models.BooleanField(_('superuser status'))
    last_login = models.DateTimeField(_('last login'), default=models.LazyDate())
    date_joined = models.DateTimeField(_('date joined'), default=models.LazyDate())
    groups = models.ManyToManyField(Group, blank=True,
        help_text=_("In addition to the permissions manually assigned, this user will also get all permissions granted to each group he/she is in."))
    user_permissions = models.ManyToManyField(Permission, blank=True, filter_interface=models.HORIZONTAL)
    class META:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ('username',)
        exceptions = ('SiteProfileNotAvailable',)
        admin = models.Admin(
            fields = (
                (None, {'fields': ('username', 'password')}),
                (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
                (_('Permissions'), {'fields': ('is_staff', 'is_active', 'is_superuser', 'user_permissions')}),
                (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
                (_('Groups'), {'fields': ('groups',)}),
            ),
            list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff'),
            list_filter = ('is_staff', 'is_superuser'),
            search_fields = ('username', 'first_name', 'last_name', 'email'),
        )

    def __repr__(self):
        return self.username

    def get_absolute_url(self):
        return "/users/%s/" % self.username

    def is_anonymous(self):
        return False

    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def set_password(self, raw_password):
        import sha, random
        algo = 'sha1'
        salt = sha.new(str(random.random())).hexdigest()[:5]
        hsh = sha.new(salt+raw_password).hexdigest()
        self.password = '%s$%s$%s' % (algo, salt, hsh)

    def check_password(self, raw_password):
        """
        Returns a boolean of whether the raw_password was correct. Handles
        encryption formats behind the scenes.
        """
        # Backwards-compatibility check. Older passwords won't include the
        # algorithm or salt.
        if '$' not in self.password:
            import md5
            is_correct = (self.password == md5.new(raw_password).hexdigest())
            if is_correct:
                # Convert the password to the new, more secure format.
                self.set_password(raw_password)
                self.save()
            return is_correct
        algo, salt, hsh = self.password.split('$')
        if algo == 'md5':
            import md5
            return hsh == md5.new(salt+raw_password).hexdigest()
        elif algo == 'sha1':
            import sha
            return hsh == sha.new(salt+raw_password).hexdigest()
        raise ValueError, "Got unknown password algorithm type in password."

    def get_group_permissions(self):
        "Returns a list of permission strings that this user has through his/her groups."
        if not hasattr(self, '_group_perm_cache'):
            import sets
            cursor = db.cursor()
            # The SQL below works out to the following, after DB quoting:
            # cursor.execute("""
            #     SELECT p.package, p.codename
            #     FROM auth_permissions p, auth_groups_permissions gp, auth_users_groups ug
            #     WHERE p.id = gp.permission_id
            #         AND gp.group_id = ug.group_id
            #         AND ug.user_id = %s""", [self.id])
            sql = """
                SELECT p.%s, p.%s
                FROM %s p, %s gp, %s ug
                WHERE p.%s = gp.%s
                    AND gp.%s = ug.%s
                    AND ug.%s = %%s""" % (
                db.quote_name('package'), db.quote_name('codename'),
                db.quote_name('auth_permissions'), db.quote_name('auth_groups_permissions'),
                db.quote_name('auth_users_groups'), db.quote_name('id'),
                db.quote_name('permission_id'), db.quote_name('group_id'),
                db.quote_name('group_id'), db.quote_name('user_id'))
            cursor.execute(sql, [self.id])
            self._group_perm_cache = sets.Set(["%s.%s" % (row[0], row[1]) for row in cursor.fetchall()])
        return self._group_perm_cache

    def get_all_permissions(self):
        if not hasattr(self, '_perm_cache'):
            import sets
            self._perm_cache = sets.Set(["%s.%s" % (p.package_id, p.codename) for p in self.get_permission_list()])
            self._perm_cache.update(self.get_group_permissions())
        return self._perm_cache

    def has_perm(self, perm):
        "Returns True if the user has the specified permission."
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        return perm in self.get_all_permissions()

    def has_perms(self, perm_list):
        "Returns True if the user has each of the specified permissions."
        for perm in perm_list:
            if not self.has_perm(perm):
                return False
        return True

    def has_module_perms(self, package_name):
        "Returns True if the user has any permissions in the given package."
        if self.is_superuser:
            return True
        return bool(len([p for p in self.get_all_permissions() if p[:p.index('.')] == package_name]))

    def get_and_delete_messages(self):
        messages = []
        for m in self.get_message_list():
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
            from django.conf.settings import AUTH_PROFILE_MODULE
            if not AUTH_PROFILE_MODULE:
                raise SiteProfileNotAvailable
            try:
                app, mod = AUTH_PROFILE_MODULE.split('.')
                module = __import__('ellington.%s.apps.%s' % (app, mod), [], [], [''])
                self._profile_cache = module.get_object(user_id=self.id)
            except ImportError:
                try:
                    module = __import__('django.models.%s' % AUTH_PROFILE_MODULE, [], [], [''])
                    self._profile_cache = module.get_object(user__id__exact=self.id)
                except ImportError:
                    raise SiteProfileNotAvailable
        return self._profile_cache

    def _module_create_user(username, email, password):
        "Creates and saves a User with the given username, e-mail and password."
        now = datetime.datetime.now()
        user = User(None, username, '', '', email.strip().lower(), 'placeholder', False, True, False, now, now)
        user.set_password(password)
        user.save()
        return user

    def _module_make_random_password(length=10, allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'):
        "Generates a random password with the given length and given allowed_chars"
        # Note that default value of allowed_chars does not have "I" or letters
        # that look like it -- just to avoid confusion.
        from random import choice
        return ''.join([choice(allowed_chars) for i in range(length)])

class Message(models.Model):
    user = models.ForeignKey(User)
    message = models.TextField(_('Message'))

    def __repr__(self):
        return self.message
