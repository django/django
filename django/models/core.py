import base64, md5, random, sys
import cPickle as pickle
from django.db import models
from django.utils.translation import gettext_lazy as _

class SiteManager(models.Manager):
    def get_current(self):
        from django.conf.settings import SITE_ID
        return self.get_object(pk=SITE_ID)

class Site(models.Model):
    domain = models.CharField(_('domain name'), maxlength=100)
    name = models.CharField(_('display name'), maxlength=50)
    objects = SiteManager()
    class META:
        verbose_name = _('site')
        verbose_name_plural = _('sites')
        db_table = 'sites'
        ordering = ('domain',)
        admin = models.Admin(
            list_display = ('domain', 'name'),
            search_fields = ('domain', 'name'),
        )

    def __repr__(self):
        return self.domain

class Package(models.Model):
    label = models.CharField(_('label'), maxlength=20, primary_key=True)
    name = models.CharField(_('name'), maxlength=30, unique=True)
    class META:
        verbose_name = _('package')
        verbose_name_plural = _('packages')
        db_table = 'packages'
        ordering = ('name',)

    def __repr__(self):
        return self.name

class ContentType(models.Model):
    name = models.CharField(_('name'), maxlength=100)
    package = models.ForeignKey(Package, db_column='package')
    python_module_name = models.CharField(_('python module name'), maxlength=50)
    class META:
        verbose_name = _('content type')
        verbose_name_plural = _('content types')
        db_table = 'content_types'
        ordering = ('package', 'name')
        unique_together = (('package', 'python_module_name'),)

    def __repr__(self):
        return "%s | %s" % (self.package_id, self.name)

    def get_model_module(self):
        "Returns the Python model module for accessing this type of content."
        return __import__('django.models.%s.%s' % (self.package_id, self.python_module_name), '', '', [''])

    def get_object_for_this_type(self, **kwargs):
        """
        Returns an object of this type for the keyword arguments given.
        Basically, this is a proxy around this object_type's get_object() model
        method. The ObjectNotExist exception, if thrown, will not be caught,
        so code that calls this method should catch it.
        """
        return self.get_model_module().get_object(**kwargs)

class SessionManager(models.Manager):
    def encode(self, session_dict):
        "Returns the given session dictionary pickled and encoded as a string."
        from django.conf.settings import SECRET_KEY
        pickled = pickle.dumps(session_dict)
        pickled_md5 = md5.new(pickled + SECRET_KEY).hexdigest()
        return base64.encodestring(pickled + pickled_md5)

    def get_new_session_key(self):
        "Returns session key that isn't being used."
        from django.conf.settings import SECRET_KEY
        # The random module is seeded when this Apache child is created.
        # Use person_id and SECRET_KEY as added salt.
        while 1:
            session_key = md5.new(str(random.randint(0, sys.maxint - 1)) + SECRET_KEY).hexdigest()
            try:
                self.get_object(session_key__exact=session_key)
            except self.klass.DoesNotExist:
                break
        return session_key

    def save(self, session_key, session_dict, expire_date):
        s = self.klass(session_key, self.encode(session_dict), expire_date)
        if session_dict:
            s.save()
        else:
            s.delete() # Clear sessions with no data.
        return s

class Session(models.Model):
    session_key = models.CharField(_('session key'), maxlength=40, primary_key=True)
    session_data = models.TextField(_('session data'))
    expire_date = models.DateTimeField(_('expire date'))
    objects = SessionManager()
    class META:
        verbose_name = _('session')
        verbose_name_plural = _('sessions')
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
        try:
            return pickle.loads(pickled)
        # Unpickling can cause a variety of exceptions. If something happens,
        # just return an empty dictionary (an empty session).
        except:
            return {}
