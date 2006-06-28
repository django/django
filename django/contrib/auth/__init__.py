LOGIN_URL = '/accounts/login/'
REDIRECT_FIELD_NAME = 'next'

class NoMatchFound(Exception): pass

class HasPermission(object):
    """
    Function that supports multiple implementations via a type registry. The 
    implemetation called depends on the argument types.
    """
    def __init__(self):
        self.registry = {}

    def __call__(self, user, permission, obj=None):
        # TODO: this isn't very robust. Only matches on exact types. Support 
        # for matching subclasses and caching registry hits would be helpful,
        # but we'll add that later
        types = (type(user), type(permission), type(obj))
        func = self.registry.get(types)
        if func is not None:
            return func(user, permission, obj)
        else:
            raise NoMatchFound, "%s\n%s" % (self.registry, types)

    def register(self, user_type, permission_type, obj_type, func):
        types = (user_type, permission_type, obj_type)
        self.registry[types] = func

has_permission = HasPermission()
