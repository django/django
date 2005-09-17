# Specialized template classes for Django, decoupled from the basic template system.

from django.core.template import Context
from django.conf.settings import DEBUG, INTERNAL_IPS

class DjangoContext(Context):
    """
    This subclass of template.Context automatically populates 'user' and
    'messages' in the context.
    """
    def __init__(self, request, dict=None):
        Context.__init__(self, dict)
        self['user'] = request.user
        self['messages'] = request.user.get_and_delete_messages()
        self['perms'] = PermWrapper(request.user)
        if DEBUG and request.META.get('REMOTE_ADDR') in INTERNAL_IPS:
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
