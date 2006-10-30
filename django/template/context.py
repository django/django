from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

_standard_context_processors = None

class ContextPopException(Exception):
    "pop() has been called more times than push()"
    pass

class Context(object):
    "A stack container for variable context"
    def __init__(self, dict_=None):
        dict_ = dict_ or {}
        self.dicts = [dict_]

    def __repr__(self):
        return repr(self.dicts)

    def __iter__(self):
        for d in self.dicts:
            yield d

    def push(self):
        self.dicts = [{}] + self.dicts

    def pop(self):
        if len(self.dicts) == 1:
            raise ContextPopException
        del self.dicts[0]

    def __setitem__(self, key, value):
        "Set a variable in the current context"
        self.dicts[0][key] = value

    def __getitem__(self, key):
        "Get a variable's value, starting at the current context and going upward"
        for d in self.dicts:
            if d.has_key(key):
                return d[key]
        raise KeyError(key)

    def __delitem__(self, key):
        "Delete a variable from the current context"
        del self.dicts[0][key]

    def has_key(self, key):
        for d in self.dicts:
            if d.has_key(key):
                return True
        return False

    def get(self, key, otherwise=None):
        for d in self.dicts:
            if d.has_key(key):
                return d[key]
        return otherwise

    def update(self, other_dict):
        "Like dict.update(). Pushes an entire dictionary's keys and values onto the context."
        self.dicts = [other_dict] + self.dicts

# This is a function rather than module-level procedural code because we only
# want it to execute if somebody uses RequestContext.
def get_standard_processors():
    global _standard_context_processors
    if _standard_context_processors is None:
        processors = []
        for path in settings.TEMPLATE_CONTEXT_PROCESSORS:
            i = path.rfind('.')
            module, attr = path[:i], path[i+1:]
            try:
                mod = __import__(module, {}, {}, [attr])
            except ImportError, e:
                raise ImproperlyConfigured, 'Error importing request processor module %s: "%s"' % (module, e)
            try:
                func = getattr(mod, attr)
            except AttributeError:
                raise ImproperlyConfigured, 'Module "%s" does not define a "%s" callable request processor' % (module, attr)
            processors.append(func)
        _standard_context_processors = tuple(processors)
    return _standard_context_processors

class RequestContext(Context):
    """
    This subclass of template.Context automatically populates itself using
    the processors defined in TEMPLATE_CONTEXT_PROCESSORS.
    Additional processors can be specified as a list of callables
    using the "processors" keyword argument.
    """
    def __init__(self, request, dict=None, processors=None):
        Context.__init__(self, dict)
        if processors is None:
            processors = ()
        else:
            processors = tuple(processors)
        for processor in get_standard_processors() + processors:
            self.update(processor(request))
