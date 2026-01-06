# Django Built-in Signals Reference

Complete reference for all signals provided by Django.

## Table of Contents

- [Model Signals](#model-signals)
- [Request/Response Signals](#requestresponse-signals)
- [Management Signals](#management-signals)
- [Database Signals](#database-signals)
- [Test Signals](#test-signals)
- [Template Signals](#template-signals)

## Model Signals

### django.db.models.signals.pre_init

Sent at the beginning of a model's `__init__()` method.

**Arguments:**
- `sender`: Model class
- `args`: Positional arguments passed to `__init__()`
- `kwargs`: Keyword arguments passed to `__init__()`

**Example:**
```python
from django.db.models.signals import pre_init
from django.dispatch import receiver
from myapp.models import Article

@receiver(pre_init, sender=Article)
def article_pre_init(sender, *args, **kwargs):
    print(f"About to initialize {sender.__name__}")
    print(f"Arguments: {kwargs}")
```

**Use cases:**
- Logging object instantiation
- Modifying initialization arguments
- Debugging model creation

### django.db.models.signals.post_init

Sent at the end of a model's `__init__()` method.

**Arguments:**
- `sender`: Model class
- `instance`: The actual instance being initialized

**Example:**
```python
from django.db.models.signals import post_init
from django.dispatch import receiver

@receiver(post_init, sender=Article)
def article_post_init(sender, instance, **kwargs):
    # Store original values for change tracking
    instance._original_status = instance.status
```

**Use cases:**
- Initializing computed properties
- Setting up change tracking
- Caching initial state

### django.db.models.signals.pre_save

Sent before a model's `save()` method is called.

**Arguments:**
- `sender`: Model class
- `instance`: The instance being saved
- `raw`: Boolean; True if model is saved exactly as presented (used by loaddata)
- `using`: Database alias being used
- `update_fields`: Set of fields being updated, or None

**Example:**
```python
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify

@receiver(pre_save, sender=Article)
def article_pre_save(sender, instance, **kwargs):
    # Auto-generate slug from title
    if not instance.slug:
        instance.slug = slugify(instance.title)

    # Normalize data
    instance.title = instance.title.strip()

    # Validate before saving
    if instance.status == 'published' and not instance.published_date:
        from django.utils import timezone
        instance.published_date = timezone.now()
```

**Use cases:**
- Data normalization
- Auto-generating fields (slugs, dates)
- Pre-save validation
- Computing derived values

**Important notes:**
- Don't call `save()` in pre_save (causes recursion)
- Use for field modifications, not external operations
- `raw=True` means skip signal processing (fixtures)

### django.db.models.signals.post_save

Sent after a model's `save()` method is called.

**Arguments:**
- `sender`: Model class
- `instance`: The instance that was saved
- `created`: Boolean; True if a new record was created
- `raw`: Boolean; True if model is saved exactly as presented
- `using`: Database alias being used
- `update_fields`: Set of fields being updated, or None

**Example:**
```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):
    if created:
        # Send notification only for new orders
        transaction.on_commit(
            lambda: send_order_confirmation(instance)
        )
    else:
        # Update cache for existing orders
        cache.set(f'order_{instance.pk}', instance, 3600)

    # Create audit log
    AuditLog.objects.create(
        action='created' if created else 'updated',
        model='Order',
        object_id=instance.pk,
    )
```

**Use cases:**
- Sending notifications
- Creating related objects
- Updating caches
- Audit logging
- Triggering background tasks

**Important notes:**
- Use `transaction.on_commit()` for external operations
- Check `created` flag to differentiate create vs update
- Check `update_fields` to see which fields changed
- Don't modify and save instance (causes recursion)

### django.db.models.signals.pre_delete

Sent before a model's `delete()` method is called.

**Arguments:**
- `sender`: Model class
- `instance`: The instance being deleted
- `using`: Database alias being used

**Example:**
```python
from django.db.models.signals import pre_delete
from django.dispatch import receiver

@receiver(pre_delete, sender=Image)
def image_pre_delete(sender, instance, **kwargs):
    # Store file path for cleanup after deletion
    if instance.file:
        instance._file_path = instance.file.path
```

**Use cases:**
- Storing data needed for post-delete cleanup
- Validating deletion is allowed
- Logging before deletion

### django.db.models.signals.post_delete

Sent after a model's `delete()` method is called.

**Arguments:**
- `sender`: Model class
- `instance`: The instance that was deleted (no longer in DB)
- `using`: Database alias being used

**Example:**
```python
from django.db.models.signals import post_delete
from django.dispatch import receiver
import os

@receiver(post_delete, sender=Image)
def image_post_delete(sender, instance, **kwargs):
    # Delete file from storage
    if hasattr(instance, '_file_path'):
        try:
            os.remove(instance._file_path)
        except OSError:
            pass

    # Clear cache
    cache.delete(f'image_{instance.pk}')

    # Update related counters
    if instance.gallery:
        instance.gallery.image_count -= 1
        instance.gallery.save(update_fields=['image_count'])
```

**Use cases:**
- Cleaning up files
- Clearing caches
- Updating related objects
- Audit logging
- Sending notifications

**Important notes:**
- Instance is already deleted from database
- Can't call `instance.delete()` again
- Use for cleanup, not prevention (use pre_delete for that)

### django.db.models.signals.m2m_changed

Sent when a ManyToManyField is changed.

**Arguments:**
- `sender`: Intermediate model class for the ManyToManyField
- `instance`: The instance whose many-to-many relation is updated
- `action`: String indicating the type of update:
  - `pre_add`: Before adding objects to relation
  - `post_add`: After adding objects to relation
  - `pre_remove`: Before removing objects from relation
  - `post_remove`: After removing objects from relation
  - `pre_clear`: Before clearing relation
  - `post_clear`: After clearing relation
- `reverse`: Boolean; True if relation is updated from reverse side
- `model`: The model class of objects added/removed/cleared
- `pk_set`: Set of primary keys of objects added/removed/cleared (None for clear)
- `using`: Database alias being used

**Example:**
```python
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

@receiver(m2m_changed, sender=Article.tags.through)
def article_tags_changed(sender, instance, action, pk_set, **kwargs):
    if action == 'post_add':
        # Invalidate cache when tags added
        cache.delete(f'article_tags_{instance.pk}')

        # Update tag counts
        Tag.objects.filter(pk__in=pk_set).update(
            article_count=F('article_count') + 1
        )

    elif action == 'post_remove':
        # Update tag counts when tags removed
        Tag.objects.filter(pk__in=pk_set).update(
            article_count=F('article_count') - 1
        )

    elif action == 'post_clear':
        # Rebuild all tag counts
        cache.delete(f'article_tags_{instance.pk}')
```

**Use cases:**
- Maintaining denormalized counts
- Cache invalidation
- Audit logging
- Triggering reindexing

**Important notes:**
- Fired twice per operation (pre and post)
- `pk_set` is None for clear actions
- Not fired for `QuerySet.update()`
- Use `action` to determine what happened

## Request/Response Signals

### django.core.signals.request_started

Sent when Django begins processing an HTTP request.

**Arguments:**
- `sender`: Handler class (usually WSGIHandler)
- `environ`: The environ dictionary provided to the request

**Example:**
```python
from django.core.signals import request_started
from django.dispatch import receiver
import time

@receiver(request_started)
def log_request_start(sender, environ, **kwargs):
    environ['request_start_time'] = time.time()
```

**Use cases:**
- Request timing
- Logging
- Setting up request-level context
- Initializing thread-local storage

### django.core.signals.request_finished

Sent when Django finishes delivering an HTTP response.

**Arguments:**
- `sender`: Handler class (usually WSGIHandler)

**Example:**
```python
from django.core.signals import request_finished
from django.dispatch import receiver
import time

@receiver(request_finished)
def log_request_end(sender, **kwargs):
    # Note: environ not available here
    # Use middleware for timing instead
    pass
```

**Use cases:**
- Cleanup operations
- Closing connections
- Logging request completion
- Resetting thread-local state

**Important notes:**
- Sent even if exception occurred
- No access to request or response objects
- Use middleware for request/response access

### django.core.signals.got_request_exception

Sent when Django encounters an exception while processing a request.

**Arguments:**
- `sender`: Handler class
- `request`: The HTTPRequest object (may be None)

**Example:**
```python
from django.core.signals import got_request_exception
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

@receiver(got_request_exception)
def log_exception(sender, request, **kwargs):
    logger.error(
        f"Exception processing request: {request.path if request else 'unknown'}",
        exc_info=True
    )
```

**Use cases:**
- Error logging
- Error monitoring (Sentry, etc.)
- Custom error handling
- Alerting

## Management Signals

### django.db.models.signals.pre_migrate

Sent before the `migrate` command starts to install an application.

**Arguments:**
- `sender`: AppConfig instance for app about to be migrated
- `app_config`: Same as sender
- `verbosity`: Verbosity level
- `interactive`: Boolean; True if user can provide input
- `using`: Database alias being migrated
- `plan`: List of migration operations planned
- `apps`: Apps registry with historical models

**Example:**
```python
from django.db.models.signals import pre_migrate
from django.dispatch import receiver

@receiver(pre_migrate)
def prepare_migration(sender, app_config, **kwargs):
    if app_config.name == 'myapp':
        # Create backup before migration
        print("Creating backup...")
        create_database_backup()
```

**Use cases:**
- Creating backups
- Pre-migration validation
- Setting up test data
- Database preparation

### django.db.models.signals.post_migrate

Sent after the `migrate` command finishes installing an application.

**Arguments:**
- `sender`: AppConfig instance
- `app_config`: Same as sender
- `verbosity`: Verbosity level
- `interactive`: Boolean; True if user can provide input
- `using`: Database alias
- `plan`: List of migration operations that were performed
- `apps`: Apps registry (use this, not django.apps.apps)

**Example:**
```python
from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def create_default_data(sender, app_config, using, **kwargs):
    if app_config.name == 'myapp':
        # Get models from historical apps registry
        User = apps.get_model('auth', 'User')
        Group = apps.get_model('auth', 'Group')

        # Create default groups
        Group.objects.using(using).get_or_create(name='Editors')
        Group.objects.using(using).get_or_create(name='Viewers')
```

**Use cases:**
- Creating default data
- Running data migrations
- Setting up permissions
- Initializing caches

**Important notes:**
- Use `apps` parameter, not `django.apps.apps`
- Use `using` parameter for database operations
- Idempotent operations only (may run multiple times)

## Database Signals

### django.db.backends.signals.connection_created

Sent when database connection is created.

**Arguments:**
- `sender`: Database wrapper class
- `connection`: Database connection that was opened

**Example:**
```python
from django.db.backends.signals import connection_created
from django.dispatch import receiver

@receiver(connection_created)
def setup_postgres_extensions(sender, connection, **kwargs):
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
            cursor.execute('CREATE EXTENSION IF NOT EXISTS unaccent')
```

**Use cases:**
- Database initialization
- Setting up PostgreSQL extensions
- Configuring connection settings
- Logging database connections

## Test Signals

### django.test.signals.setting_changed

Sent when settings are changed in tests (via `override_settings`).

**Arguments:**
- `sender`: Settings class
- `setting`: Name of setting that changed
- `value`: New value of setting
- `enter`: Boolean; True when entering override, False when exiting

**Example:**
```python
from django.test.signals import setting_changed
from django.dispatch import receiver

@receiver(setting_changed)
def clear_cache_on_setting_change(sender, setting, **kwargs):
    if setting == 'CACHE_MIDDLEWARE_SECONDS':
        cache.clear()
```

**Use cases:**
- Clearing caches when settings change
- Reinitializing components
- Test isolation

### django.db.backends.signals.template_rendered

Sent when a template is rendered during testing.

**Arguments:**
- `sender`: Template object
- `template`: Template that was rendered
- `context`: Context used to render template

**Example:**
```python
# Usually used via TestCase.assertTemplateUsed()
from django.test import TestCase

class ViewTests(TestCase):
    def test_home_page(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'home.html')
```

**Use cases:**
- Template testing
- Context verification
- Debugging template rendering

## Template Signals

### django.template.base.template_rendered

Sent when a template is rendered.

**Arguments:**
- `sender`: Template instance
- `template`: Template instance
- `context`: Context used for rendering

**Example:**
```python
from django.template.base import template_rendered
from django.dispatch import receiver

@receiver(template_rendered)
def log_template_usage(sender, template, context, **kwargs):
    if hasattr(template, 'name'):
        print(f"Rendered template: {template.name}")
```

**Use cases:**
- Template analytics
- Performance monitoring
- Debug logging

## Signal Best Practices

### Always Accept **kwargs

```python
# GOOD: Forward compatible
@receiver(post_save, sender=MyModel)
def my_handler(sender, instance, created, **kwargs):
    pass

# BAD: Will break if Django adds parameters
@receiver(post_save, sender=MyModel)
def my_handler(sender, instance, created):
    pass
```

### Use Specific Senders

```python
# GOOD: Only for Article model
@receiver(post_save, sender=Article)
def article_saved(sender, instance, **kwargs):
    pass

# AVOID: Fires for all models
@receiver(post_save)
def any_model_saved(sender, instance, **kwargs):
    pass
```

### Check Action for m2m_changed

```python
# GOOD: Only process specific actions
@receiver(m2m_changed, sender=Article.tags.through)
def tags_changed(sender, instance, action, **kwargs):
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    # Process changes
```

### Use dispatch_uid for Duplicate Prevention

```python
# GOOD: Prevents duplicate connections
@receiver(post_save, sender=Article, dispatch_uid="article_post_save_unique")
def article_saved(sender, instance, **kwargs):
    pass
```

### Use transaction.on_commit() for External Operations

```python
from django.db import transaction

# GOOD: Wait for transaction commit
@receiver(post_save, sender=Order)
def send_confirmation(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(
            lambda: send_email(instance)
        )
```

## Signal Timing Diagram

```
Model.save() called
    ├─> pre_save signal sent
    ├─> Database INSERT/UPDATE
    ├─> post_save signal sent
    └─> Returns

Model.delete() called
    ├─> pre_delete signal sent
    ├─> Database DELETE
    ├─> post_delete signal sent
    └─> Returns

M2M field modified
    ├─> m2m_changed(action='pre_add') sent
    ├─> Database INSERT
    ├─> m2m_changed(action='post_add') sent
    └─> Returns
```

## Performance Notes

**Signals that run on every request:**
- `request_started`
- `request_finished`

**Signals that run on every save:**
- `pre_save`
- `post_save`

**Tips:**
- Keep signal handlers fast
- Use background tasks for heavy work
- Check conditions early and return
- Use `transaction.on_commit()` for I/O
- Consider alternatives for high-frequency operations
