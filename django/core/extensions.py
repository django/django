"Specialized Context and ModPythonRequest classes for our CMS. Use these!"

from django.core.template import Context
from django.utils.httpwrappers import ModPythonRequest
from django.conf.settings import DEBUG, INTERNAL_IPS
from pprint import pformat

class CMSContext(Context):
    """This subclass of template.Context automatically populates 'user' and
    'messages' in the context. Use this."""
    def __init__(self, request, dict={}):
        Context.__init__(self, dict)
        self['user'] = request.user
        self['messages'] = request.user.get_and_delete_messages()
        self['perms'] = PermWrapper(request.user)
        if DEBUG and request.META['REMOTE_ADDR'] in INTERNAL_IPS:
            self['debug'] = True
            from django.core import db
            self['sql_queries'] = db.db.queries

# PermWrapper and PermLookupDict proxy the permissions system into objects that
# the template system can understand.

class PermLookupDict:
    def __init__(self, user, module_name):
        self.user, self.module_name = user, module_name
    def __repr__(self):
        return str(self.user.get_permission_list())
    def __getitem__(self, perm_name):
        return self.user.has_perm("%s.%s" % (self.module_name, perm_name))
    def __nonzero__(self):
        return self.user.has_module_perms(self.module_name)

class PermWrapper:
    def __init__(self, user):
        self.user = user
    def __getitem__(self, module_name):
        return PermLookupDict(self.user, module_name)

class CMSRequest(ModPythonRequest):
    "A special version of ModPythonRequest with support for CMS sessions"
    def __init__(self, req):
        ModPythonRequest.__init__(self, req)

    def __repr__(self):
        return '<CMSRequest\npath:%s,\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s,\nuser:%s>' % \
            (self.path, pformat(self.GET), pformat(self.POST), pformat(self.COOKIES),
            pformat(self.META), pformat(self.user))

    def _load_session_and_user(self):
        from django.models.auth import sessions
        from django.conf.settings import AUTH_SESSION_COOKIE
        session_cookie = self.COOKIES.get(AUTH_SESSION_COOKIE, '')
        try:
            self._session = sessions.get_session_from_cookie(session_cookie)
            self._user = self._session.get_user()
        except sessions.SessionDoesNotExist:
            from django.parts.auth import anonymoususers
            self._session = None
            self._user = anonymoususers.AnonymousUser()

    def _get_session(self):
        if not hasattr(self, '_session'):
            self._load_session_and_user()
        return self._session

    def _set_session(self, session):
        self._session = session

    def _get_user(self):
        if not hasattr(self, '_user'):
            self._load_session_and_user()
        return self._user

    def _set_user(self, user):
        self._user = user

    session = property(_get_session, _set_session)
    user = property(_get_user, _set_user)
