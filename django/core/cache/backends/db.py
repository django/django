"Database cache backend."
import base64
from datetime import timedelta

try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.core.cache.backends.base import BaseCache
from django.db import connections, router, transaction, DatabaseError, models
from django.utils import timezone

def create_cache_model(table):
    """
    This function will create a new cache table model to use for caching. The
    model is created dynamically, and isn't part of app-loaded Django models.
    """
    class CacheEntry(models.Model):
        cache_key = models.CharField(max_length=255, unique=True, primary_key=True)
        value = models.TextField()
        expires = models.DateTimeField(db_index=True)

        class Meta:
            db_table = table
            verbose_name = 'cache entry'
            verbose_name_plural = 'cache entries'
            # We need to be able to create multiple different instances of
            # this same class, and we don't want to leak entries into the
            # app-cache. This model must not be part of the app-cache also
            # because get_models() must not list any CacheEntry classes. So
            # use this internal flag to skip this class totally.
            _skip_app_cache = True

    opts = CacheEntry._meta
    opts.app_label = 'django_cache'
    opts.module_name = 'cacheentry'
    return CacheEntry
    

class BaseDatabaseCache(BaseCache):
    def __init__(self, table, params):
        BaseCache.__init__(self, params)
        self.cache_model_class = create_cache_model(table)
        self.objects = self.cache_model_class.objects

class DatabaseCache(BaseDatabaseCache):

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        db = router.db_for_write(self.cache_model_class)
        self.validate_key(key)
        try:
            obj = self.objects.using(db).get(cache_key=key)
        except self.cache_model_class.DoesNotExist:
            return default
        now = timezone.now()
        if obj.expires < now:
            obj.delete()
            transaction.commit_unless_managed(using=db)
            return default
        # Note: we must commit_unless_managed even for read-operations to
        # avoid transaction leaks.
        transaction.commit_unless_managed(using=db)
        value = connections[db].ops.process_clob(obj.value)
        return pickle.loads(base64.decodestring(value))

    def set(self, key, value, timeout=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        self._base_set('set', key, value, timeout)

    def add(self, key, value, timeout=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return self._base_set('add', key, value, timeout)

    def _base_set(self, mode, key, value, timeout=None):
        db = router.db_for_write(self.cache_model_class)
        if timeout is None:
            timeout = self.default_timeout
        now = timezone.now()
        now = now.replace(microsecond=0)
        exp = now + timedelta(seconds=timeout)
        num = self.objects.using(db).count()
        if num > self._max_entries:
            self._cull(db, now)
        pickled = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
        encoded = base64.encodestring(pickled).strip()
        try:
            try:
                obj = self.objects.using(db).only('cache_key').get(cache_key=key)
                if mode == 'set' or (mode == 'add' and obj.expires < now):
                    obj.expires = exp
                    obj.value = encoded
                    obj.save(using=db)
                else:
                    return False
            except self.cache_model_class.DoesNotExist:
                self.objects.using(db).create(cache_key=key, expires=exp, value=encoded)
        except DatabaseError:
            # To be threadsafe, updates/inserts are allowed to fail silently
            transaction.rollback_unless_managed(using=db)
            return False
        else:
            transaction.commit_unless_managed(using=db)
            return True

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_write(self.cache_model_class)
        self.objects.using(db).filter(cache_key=key).delete()
        transaction.commit_unless_managed(using=db)

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_read(self.cache_model_class)

        now = timezone.now()
        now = now.replace(microsecond=0)
        ret = self.objects.using(db).filter(cache_key=key, expires__gt=now).exists()
        transaction.commit_unless_managed(using=db)
        return ret

    def _cull(self, db, now):
        if self._cull_frequency == 0:
            # cull might be used inside other dbcache operations possibly already
            # doing commits themselves - so do not commit in clear.
            self.clear(commit=False)
        else:
            # When USE_TZ is True, 'now' will be an aware datetime in UTC.
            self.objects.using(db).filter(expires__lt=now).delete()
            num = self.objects.using(db).count()
            if num > self._max_entries:
                cull_num = num / self._cull_frequency
                limit = self.objects.using(db).values_list(
                    'cache_key').order_by('cache_key')[cull_num][0]
                self.objects.using(db).filter(cache_key__lt=limit).delete()

    def clear(self, commit=True):
        db = router.db_for_write(self.cache_model_class)
        self.objects.using(db).delete()
        if commit:
            transaction.commit_unless_managed(using=db)

# For backwards compatibility
class CacheClass(DatabaseCache):
    pass
