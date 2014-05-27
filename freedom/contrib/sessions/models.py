from freedom.db import models
from freedom.utils.translation import ugettext_lazy as _


class SessionManager(models.Manager):
    def encode(self, session_dict):
        """
        Returns the given session dictionary serialized and encoded as a string.
        """
        return SessionStore().encode(session_dict)

    def save(self, session_key, session_dict, expire_date):
        s = self.model(session_key, self.encode(session_dict), expire_date)
        if session_dict:
            s.save()
        else:
            s.delete()  # Clear sessions with no data.
        return s


class Session(models.Model):
    """
    Freedom provides full support for anonymous sessions. The session
    framework lets you store and retrieve arbitrary data on a
    per-site-visitor basis. It stores data on the server side and
    abstracts the sending and receiving of cookies. Cookies contain a
    session ID -- not the data itself.

    The Freedom sessions framework is entirely cookie-based. It does
    not fall back to putting session IDs in URLs. This is an intentional
    design decision. Not only does that behavior make URLs ugly, it makes
    your site vulnerable to session-ID theft via the "Referer" header.

    For complete documentation on using Sessions in your code, consult
    the sessions documentation that is shipped with Freedom (also available
    on the Freedom Web site).
    """
    session_key = models.CharField(_('session key'), max_length=40,
                                   primary_key=True)
    session_data = models.TextField(_('session data'))
    expire_date = models.DateTimeField(_('expire date'), db_index=True)
    objects = SessionManager()

    class Meta:
        db_table = 'freedom_session'
        verbose_name = _('session')
        verbose_name_plural = _('sessions')

    def get_decoded(self):
        return SessionStore().decode(self.session_data)


# At bottom to avoid circular import
from freedom.contrib.sessions.backends.db import SessionStore
