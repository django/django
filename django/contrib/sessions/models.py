import base64, md5, random, sys
import cPickle as pickle
from django.db import models
from django.utils.translation import gettext_lazy as _

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
            session_key = md5.new(str(random.randint(0, sys.maxint - 1)) + str(random.randint(0, sys.maxint - 1)) + SECRET_KEY).hexdigest()
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
    class Meta:
        db_table = 'django_sessions'
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
