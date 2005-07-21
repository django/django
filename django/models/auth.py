from django.core import meta, validators
from django.models import core

class Permission(meta.Model):
    fields = (
        meta.CharField('name', 'name', maxlength=50),
        meta.ForeignKey(core.Package, name='package'),
        meta.CharField('codename', 'code name', maxlength=100),
    )
    unique_together = (('package', 'codename'),)
    ordering = (('package', 'ASC'), ('codename', 'ASC'))

    def __repr__(self):
        return "%s | %s" % (self.package, self.name)

class Group(meta.Model):
    fields = (
        meta.CharField('name', 'name', maxlength=80, unique=True),
        meta.ManyToManyField(Permission, blank=True, filter_interface=meta.HORIZONTAL),
    )
    ordering = (('name', 'ASC'),)
    admin = meta.Admin(
        search_fields = ('name',),
    )

    def __repr__(self):
        return self.name

class User(meta.Model):
    fields = (
        meta.CharField('username', 'username', maxlength=30, unique=True,
            validator_list=[validators.isAlphaNumeric]),
        meta.CharField('first_name', 'first name', maxlength=30, blank=True),
        meta.CharField('last_name', 'last name', maxlength=30, blank=True),
        meta.EmailField('email', 'e-mail address', blank=True),
        meta.CharField('password_md5', 'password', maxlength=32, help_text="Use an MD5 hash -- not the raw password."),
        meta.BooleanField('is_staff', 'staff status',
            help_text="Designates whether the user can log into this admin site."),
        meta.BooleanField('is_active', 'active', default=True),
        meta.BooleanField('is_superuser', 'superuser status'),
        meta.DateTimeField('last_login', 'last login', default=meta.LazyDate()),
        meta.DateTimeField('date_joined', 'date joined', default=meta.LazyDate()),
        meta.ManyToManyField(Group, blank=True,
            help_text="In addition to the permissions manually assigned, this user will also get all permissions granted to each group he/she is in."),
        meta.ManyToManyField(Permission, name='user_permissions', blank=True, filter_interface=meta.HORIZONTAL),
    )
    ordering = (('username', 'ASC'),)
    exceptions = ('SiteProfileNotAvailable',)
    admin = meta.Admin(
        fields = (
            (None, {'fields': ('username', 'password_md5')}),
            ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
            ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'user_permissions')}),
            ('Important dates', {'fields': ('last_login', 'date_joined')}),
            ('Groups', {'fields': ('groups',)}),
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
        import md5
        self.password_md5 = md5.new(raw_password).hexdigest()

    def check_password(self, raw_password):
        "Returns a boolean of whether the raw_password was correct."
        import md5
        return self.password_md5 == md5.new(raw_password).hexdigest()

    def get_group_permissions(self):
        "Returns a list of permission strings that this user has through his/her groups."
        if not hasattr(self, '_group_perm_cache'):
            import sets
            cursor = db.cursor()
            cursor.execute("""
                SELECT p.package, p.codename
                FROM auth_permissions p, auth_groups_permissions gp, auth_users_groups ug
                WHERE p.id = gp.permission_id
                    AND gp.group_id = ug.group_id
                    AND ug.user_id = %s""", [self.id])
            self._group_perm_cache = sets.Set(["%s.%s" % (row[0], row[1]) for row in cursor.fetchall()])
        return self._group_perm_cache

    def get_all_permissions(self):
        if not hasattr(self, '_perm_cache'):
            import sets
            self._perm_cache = sets.Set(["%s.%s" % (p.package, p.codename) for p in self.get_permission_list()])
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
                    self._profile_cache = module.get_object(user_id__exact=self.id)
                except ImportError:
                    raise SiteProfileNotAvailable
        return self._profile_cache

    def _module_create_user(username, email, password):
        "Creates and saves a User with the given username, e-mail and password."
        import md5
        password_md5 = md5.new(password).hexdigest()
        now = datetime.datetime.now()
        user = User(None, username, '', '', email.strip().lower(), password_md5, False, True, False, now, now)
        user.save()
        return user

    def _module_make_random_password(length=10, allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'):
        "Generates a random password with the given length and given allowed_chars"
        # Note that default value of allowed_chars does not have "I" or letters
        # that look like it -- just to avoid confusion.
        from random import choice
        return ''.join([choice(allowed_chars) for i in range(length)])

class Session(meta.Model):
    fields = (
        meta.ForeignKey(User),
        meta.CharField('session_md5', 'session MD5 hash', maxlength=32),
        meta.DateTimeField('start_time', 'start time', auto_now=True),
    )
    module_constants = {
        'TEST_COOKIE_NAME': 'testcookie',
        'TEST_COOKIE_VALUE': 'worked',
    }

    def __repr__(self):
        return "session started at %s" % self.start_time

    def get_cookie(self):
        "Returns a tuple of the cookie name and value for this session."
        from django.conf.settings import AUTH_SESSION_COOKIE, SECRET_KEY
        import md5
        return AUTH_SESSION_COOKIE, self.session_md5 + md5.new(self.session_md5 + SECRET_KEY + 'auth').hexdigest()

    def _module_create_session(user_id):
        "Registers a session and returns the session_md5."
        from django.conf.settings import SECRET_KEY
        import md5, random, sys
        # The random module is seeded when this Apache child is created.
        # Use person_id and SECRET_KEY as added salt.
        session_md5 = md5.new(str(random.randint(user_id, sys.maxint - 1)) + SECRET_KEY).hexdigest()
        s = Session(None, user_id, session_md5, None)
        s.save()
        return s

    def _module_get_session_from_cookie(session_cookie_string):
        from django.conf.settings import SECRET_KEY
        import md5
        if not session_cookie_string:
            raise SessionDoesNotExist
        session_md5, tamper_check = session_cookie_string[:32], session_cookie_string[32:]
        if md5.new(session_md5 + SECRET_KEY + 'auth').hexdigest() != tamper_check:
            raise SessionDoesNotExist
        return get_object(session_md5__exact=session_md5, select_related=True)

    def _module_destroy_all_sessions(user_id):
        "Destroys all sessions for a user, logging out all computers."
        for session in get_list(user_id__exact=user_id):
            session.delete()

    def _module_start_web_session(user_id, request, response):
        "Sets the necessary cookie in the given HttpResponse object, also updates last login time for user."
        from django.models.auth import users
        from django.conf.settings import REGISTRATION_COOKIE_DOMAIN
        user = users.get_object(id__exact=user_id)
        user.last_login = datetime.datetime.now()
        user.save()
        session = create_session(user_id)
        key, value = session.get_cookie()
        cookie_domain = REGISTRATION_COOKIE_DOMAIN or None
        response.set_cookie(key, value, domain=cookie_domain)

class Message(meta.Model):
    fields = (
        meta.AutoField('id', 'ID', primary_key=True),
        meta.ForeignKey(User),
        meta.TextField('message', 'message'),
    )

    def __repr__(self):
        return self.message

class LogEntry(meta.Model):
    module_name = 'log'
    verbose_name_plural = 'log entries'
    db_table = 'auth_admin_log'
    fields = (
        meta.DateTimeField('action_time', 'action time', auto_now=True),
        meta.ForeignKey(User),
        meta.ForeignKey(core.ContentType, name='content_type_id', rel_name='content_type', blank=True, null=True),
        meta.IntegerField('object_id', 'object ID', blank=True, null=True),
        meta.CharField('object_repr', 'object representation', maxlength=200),
        meta.PositiveSmallIntegerField('action_flag', 'action flag'),
        meta.TextField('change_message', 'change message', blank=True),
    )
    ordering = (('action_time', 'DESC'),)
    module_constants = {
        'ADDITION': 1,
        'CHANGE': 2,
        'DELETION': 3,
    }

    def __repr__(self):
        return str(self.action_time)

    def is_addition(self):
        return self.action_flag == ADDITION

    def is_change(self):
        return self.action_flag == CHANGE

    def is_deletion(self):
        return self.action_flag == DELETION

    def get_edited_object(self):
        "Returns the edited object represented by this log entry"
        return self.get_content_type().get_object_for_this_type(id__exact=self.object_id)

    def get_admin_url(self):
        """
        Returns the admin URL to edit the object represented by this log entry.
        This is relative to the Django admin index page.
        """
        return "%s/%s/%s/" % (self.get_content_type().package, self.get_content_type().python_module_name, self.object_id)

    def _module_log_action(user_id, content_type_id, object_id, object_repr, action_flag, change_message=''):
        e = LogEntry(None, None, user_id, content_type_id, object_id, object_repr[:200], action_flag, change_message)
        e.save()
