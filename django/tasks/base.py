from __future__ import unicode_literals

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_by_path


DEFAULT_TASK_ALIAS = 'default'

# backends cache to make sure we don't create one per connection
# all the backends should be thread-safe
backends = {}

class InvalidTaskBackendError(Exception):
    pass

def _create_task_backend(alias):
    try:
        conf = settings.QUEUES[alias]
    except KeyError:
        raise ImproperlyConfigured("%s is not defined in QUEUES" % alias)

    args = conf.copy()
    backend = args.pop('BACKEND')
    try:
        # import the given backend
        backend_cls = import_by_path(backend)
    except ImproperlyConfigured as e:
        raise InvalidTaskBackendError("Could not find backend '%s': %s" % (
            backend, e))

    return backend_cls(alias, **args)

def get_backend(alias=None):
    # note that this code is similar to django.core.cache.CacheHandler and
    # might benefit from refactoring
    if not alias:
        alias = DEFAULT_TASK_ALIAS

    try:
        return backends[alias]
    except KeyError:
        pass

    backends[alias] = _create_task_backend(alias)
    return backends[alias]

class Task(object):
    def __init__(self, func=None, name=None, using=None, options=None):
        if not func and not (hasattr(self, 'run') and hasattr(self, 'name')):
            raise
        self.run = func
        self.alias = using
        self.options = options or {}
        if name is not None:
            self.name = name
        # name hasn't been defined on class
        elif not hasattr(self, 'name'):
            n = getattr(func, '__name__', func.__class__.__name__)
            self.name = '%s.%s' % (func.__module__, n)

    def __repr__(self):
        return "<task %s>" % self.name

    @property
    def backend(self):
        return get_backend(self.alias)

    def clone(self, using=None, **options):
        opts = self.options.copy()
        opts.update(options)
        d = {
            'func': self.run,
            'name': self.name,
            'using': using or self.alias,
            'options': opts
        }
        return Task(**d)

    def delay(self, *args, **kwargs):
        return self.backend.delay(self, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        # call it right away
        return self.run(*args, **kwargs)

