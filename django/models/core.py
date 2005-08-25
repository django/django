from django.core import meta, validators

class Site(meta.Model):
    domain = meta.CharField('domain name', maxlength=100)
    name = meta.CharField('display name', maxlength=50)
    class META:
        db_table = 'sites'
        ordering = ('domain',)

    def __repr__(self):
        return self.domain

    def _module_get_current():
        "Returns the current site, according to the SITE_ID constant."
        from django.conf.settings import SITE_ID
        return get_object(pk=SITE_ID)

class Package(meta.Model):
    label = meta.CharField(maxlength=20, primary_key=True)
    name = meta.CharField(maxlength=30, unique=True)
    class META:
        db_table = 'packages'
        ordering = ('name',)

    def __repr__(self):
        return self.name

class ContentType(meta.Model):
    name = meta.CharField(maxlength=100)
    package = meta.ForeignKey(Package, db_column='package')
    python_module_name = meta.CharField(maxlength=50)
    class META:
        db_table = 'content_types'
        ordering = ('package', 'name')
        unique_together = (('package', 'python_module_name'),)

    def __repr__(self):
        return "%s | %s" % (self.package, self.name)

    def get_model_module(self):
        "Returns the Python model module for accessing this type of content."
        return __import__('django.models.%s.%s' % (self.package, self.python_module_name), '', '', [''])

    def get_object_for_this_type(self, **kwargs):
        """
        Returns an object of this type for the keyword arguments given.
        Basically, this is a proxy around this object_type's get_object() model
        method. The ObjectNotExist exception, if thrown, will not be caught,
        so code that calls this method should catch it.
        """
        return self.get_model_module().get_object(**kwargs)

class Redirect(meta.Model):
    site = meta.ForeignKey(Site, radio_admin=meta.VERTICAL)
    old_path = meta.CharField('redirect from', maxlength=200, db_index=True,
        help_text="This should be an absolute path, excluding the domain name. Example: '/events/search/'.")
    new_path = meta.CharField('redirect to', maxlength=200, blank=True,
        help_text="This can be either an absolute path (as above) or a full URL starting with 'http://'.")
    class META:
        db_table = 'redirects'
        unique_together=(('site', 'old_path'),)
        ordering = ('old_path',)
        admin = meta.Admin(
            list_filter = ('site',),
            search_fields = ('old_path', 'new_path'),
        )

    def __repr__(self):
        return "%s ---> %s" % (self.old_path, self.new_path)

class FlatFile(meta.Model):
    url = meta.CharField('URL', maxlength=100, validator_list=[validators.isAlphaNumericURL],
        help_text="Example: '/about/contact/'. Make sure to have leading and trailing slashes.")
    title = meta.CharField(maxlength=200)
    content = meta.TextField()
    enable_comments = meta.BooleanField()
    template_name = meta.CharField(maxlength=70, blank=True,
        help_text="Example: 'flatfiles/contact_page'. If this isn't provided, the system will use 'flatfiles/default'.")
    registration_required = meta.BooleanField(help_text="If this is checked, only logged-in users will be able to view the page.")
    sites = meta.ManyToManyField(Site)
    class META:
        db_table = 'flatfiles'
        verbose_name = 'flat page'
        ordering = ('url',)
        admin = meta.Admin(
            fields = (
                (None, {'fields': ('url', 'title', 'content', 'sites')}),
                ('Advanced options', {'classes': 'collapse', 'fields': ('enable_comments', 'registration_required', 'template_name')}),
            ),
            list_filter = ('sites',),
            search_fields = ('url', 'title'),
        )

    def __repr__(self):
        return "%s -- %s" % (self.url, self.title)

    def get_absolute_url(self):
        return self.url

import base64, md5, random, sys
import cPickle as pickle

class Session(meta.Model):
    session_key = meta.CharField(maxlength=40, primary_key=True)
    session_data = meta.TextField()
    expire_date = meta.DateTimeField()
    class META:
        module_constants = {
            'base64': base64,
            'md5': md5,
            'pickle': pickle,
            'random': random,
            'sys': sys,
        }

    def get_decoded(self):
        from django.conf.settings import SECRET_KEY
        encoded_data = base64.decodestring(self.session_data)
        pickled, tamper_check = encoded_data[:-32], encoded_data[-32:]
        if md5.new(pickled + SECRET_KEY).hexdigest() != tamper_check:
            from django.core.exceptions import SuspiciousOperation
            raise SuspiciousOperation, "User tampered with session cookie."
        return pickle.loads(pickled)

    def _module_encode(session_dict):
        "Returns the given session dictionary pickled and encoded as a string."
        from django.conf.settings import SECRET_KEY
        pickled = pickle.dumps(session_dict)
        pickled_md5 = md5.new(pickled + SECRET_KEY).hexdigest()
        return base64.encodestring(pickled + pickled_md5)

    def _module_get_new_session_key():
        "Returns session key that isn't being used."
        from django.conf.settings import SECRET_KEY
        # The random module is seeded when this Apache child is created.
        # Use person_id and SECRET_KEY as added salt.
        while 1:
            session_key = md5.new(str(random.randint(0, sys.maxint - 1)) + SECRET_KEY).hexdigest()
            try:
                get_object(session_key__exact=session_key)
            except SessionDoesNotExist:
                break
        return session_key

    def _module_save(session_key, session_dict, expire_date):
        s = Session(session_key, encode(session_dict), expire_date)
        if session_dict:
            s.save()
        else:
            s.delete() # Clear sessions with no data.
        return s
