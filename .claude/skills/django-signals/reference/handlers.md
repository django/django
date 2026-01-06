# Signal Handler Patterns

Complete guide to writing and organizing signal receivers/handlers.

## Table of Contents

- [Basic Handler Patterns](#basic-handler-patterns)
- [Connection Methods](#connection-methods)
- [Handler Organization](#handler-organization)
- [Advanced Handler Patterns](#advanced-handler-patterns)
- [Error Handling](#error-handling)
- [Performance Optimization](#performance-optimization)
- [Debugging](#debugging)

## Basic Handler Patterns

### Decorator-Based Receiver (Recommended)

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from myapp.models import Article

@receiver(post_save, sender=Article)
def article_post_save_handler(sender, instance, created, **kwargs):
    """Handle Article post_save signal."""
    if created:
        notify_editors(instance)
    else:
        invalidate_cache(instance)
```

**Benefits:**
- Clean and declarative
- Easy to read and maintain
- Automatic connection in `apps.py`
- IDE-friendly

### Multiple Signals, One Handler

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Article)
@receiver(post_delete, sender=Article)
def article_changed(sender, instance, **kwargs):
    """Handle any change to Article."""
    clear_article_cache()
    update_search_index()
```

### Multiple Senders, One Handler

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from myapp.models import Article, BlogPost, NewsItem

@receiver(post_save, sender=Article)
@receiver(post_save, sender=BlogPost)
@receiver(post_save, sender=NewsItem)
def content_saved(sender, instance, created, **kwargs):
    """Handle save for any content type."""
    if created:
        update_content_feed(instance)
```

### Conditional Handler

```python
@receiver(post_save, sender=Order)
def order_saved(sender, instance, created, **kwargs):
    """Handle Order saves, but only for specific conditions."""

    # Early returns for conditions we don't care about
    if not created:
        return  # Only process new orders

    if instance.status != 'pending':
        return  # Only process pending orders

    if instance.total < 100:
        return  # Only process orders over $100

    # Main handler logic
    send_high_value_order_alert(instance)
```

## Connection Methods

### Method 1: Decorator with apps.py Import

```python
# myapp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from myapp.models import Article

@receiver(post_save, sender=Article)
def article_saved(sender, instance, created, **kwargs):
    print(f"Article {instance.pk} was saved")

# myapp/apps.py
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = 'myapp'

    def ready(self):
        import myapp.signals  # noqa: F401
```

**Best for:** Most use cases. Clean and maintainable.

### Method 2: Manual connect() Call

```python
# myapp/signals.py
from django.db.models.signals import post_save
from myapp.models import Article

def article_saved(sender, instance, created, **kwargs):
    print(f"Article {instance.pk} was saved")

# Connect manually
post_save.connect(article_saved, sender=Article)
```

**Best for:**
- Dynamic handler registration
- Conditional connection
- Testing scenarios

### Method 3: Manual connect() in ready()

```python
# myapp/signals.py
def article_saved(sender, instance, created, **kwargs):
    print(f"Article {instance.pk} was saved")

# myapp/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_save

class MyAppConfig(AppConfig):
    name = 'myapp'

    def ready(self):
        from myapp.models import Article
        from myapp.signals import article_saved

        post_save.connect(article_saved, sender=Article)
```

**Best for:**
- Avoiding circular imports
- Connecting signals from other apps
- Complex initialization logic

### Method 4: Using dispatch_uid

```python
@receiver(
    post_save,
    sender=Article,
    dispatch_uid="article_post_save_unique_id"
)
def article_saved(sender, instance, created, **kwargs):
    print(f"Article {instance.pk} was saved")
```

**Purpose:** Prevents duplicate connections if handler is imported multiple times.

**Best practice:** Always use `dispatch_uid` for handlers that might be imported multiple times.

## Handler Organization

### Small App Structure

```python
# myapp/
# ├── models.py
# ├── signals.py      # All signals and handlers
# ├── apps.py
# └── tests.py

# myapp/signals.py
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Article, Comment

@receiver(post_save, sender=Article)
def article_saved(sender, instance, created, **kwargs):
    pass

@receiver(post_save, sender=Comment)
def comment_saved(sender, instance, created, **kwargs):
    pass

@receiver(pre_delete, sender=Article)
def article_deleted(sender, instance, **kwargs):
    pass
```

### Medium App Structure

```python
# myapp/
# ├── models.py
# ├── signals/
# │   ├── __init__.py
# │   ├── article_signals.py
# │   ├── comment_signals.py
# │   └── user_signals.py
# ├── apps.py
# └── tests/

# myapp/signals/__init__.py
from .article_signals import *  # noqa
from .comment_signals import *  # noqa
from .user_signals import *  # noqa

# myapp/signals/article_signals.py
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from myapp.models import Article

@receiver(post_save, sender=Article, dispatch_uid="article_post_save")
def article_saved(sender, instance, created, **kwargs):
    pass

@receiver(pre_delete, sender=Article, dispatch_uid="article_pre_delete")
def article_deleted(sender, instance, **kwargs):
    pass
```

### Large App Structure (Separate Handlers)

```python
# myapp/
# ├── models.py
# ├── signals/
# │   ├── __init__.py
# │   ├── definitions.py     # Signal definitions
# │   ├── handlers/
# │   │   ├── __init__.py
# │   │   ├── article_handlers.py
# │   │   ├── comment_handlers.py
# │   │   └── notification_handlers.py
# ├── apps.py
# └── tests/

# myapp/signals/definitions.py
from django.dispatch import Signal

article_published = Signal()
comment_approved = Signal()

# myapp/signals/handlers/__init__.py
from .article_handlers import *  # noqa
from .comment_handlers import *  # noqa
from .notification_handlers import *  # noqa

# myapp/signals/handlers/article_handlers.py
from django.dispatch import receiver
from myapp.signals.definitions import article_published

@receiver(article_published, dispatch_uid="send_article_notification")
def send_publication_notification(sender, article, **kwargs):
    """Send email when article is published."""
    notify_subscribers(article)

@receiver(article_published, dispatch_uid="update_article_search")
def update_search_index(sender, article, **kwargs):
    """Update search index when article published."""
    index_article(article)

# myapp/signals/__init__.py
from .definitions import *  # noqa
from . import handlers  # noqa: F401 - ensures handlers are imported
```

## Advanced Handler Patterns

### Class-Based Handlers

```python
class ArticleSignalHandler:
    """Handler for Article-related signals."""

    def __init__(self):
        self.notification_count = 0

    @receiver(post_save, sender=Article, dispatch_uid="article_saved_handler")
    def handle_save(self, sender, instance, created, **kwargs):
        """Handle Article save."""
        if created:
            self.send_notification(instance)
        else:
            self.update_cache(instance)

    def send_notification(self, article):
        """Send notification for new article."""
        send_email(f"New article: {article.title}")
        self.notification_count += 1

    def update_cache(self, article):
        """Update cache for existing article."""
        cache.set(f'article_{article.pk}', article, 3600)

# Instantiate to register handlers
article_handler = ArticleSignalHandler()
```

**Benefits:**
- Shared state between handlers
- Better organization for complex logic
- Easier testing (can mock methods)

**Drawbacks:**
- More complex
- Harder to understand at a glance

### Handler with Dependency Injection

```python
class NotificationService:
    def __init__(self, email_backend, sms_backend):
        self.email_backend = email_backend
        self.sms_backend = sms_backend

    def send_notification(self, user, message):
        self.email_backend.send(user.email, message)
        if user.phone:
            self.sms_backend.send(user.phone, message)

# Create service instance
notification_service = NotificationService(
    email_backend=EmailBackend(),
    sms_backend=SMSBackend()
)

# Handler uses service
@receiver(post_save, sender=Order, dispatch_uid="order_notification")
def notify_order_created(sender, instance, created, **kwargs):
    if created:
        notification_service.send_notification(
            instance.customer,
            f"Order #{instance.pk} created"
        )
```

### Handler with State Machine

```python
from django.db.models.signals import pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=Order, dispatch_uid="order_state_transition")
def handle_order_state_transition(sender, instance, **kwargs):
    """Handle Order state transitions."""

    # Get old state
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            old_status = old_instance.status
        except Order.DoesNotExist:
            old_status = None
    else:
        old_status = None

    new_status = instance.status

    # Handle state transitions
    if old_status != new_status:
        handle_status_change(instance, old_status, new_status)

def handle_status_change(order, old_status, new_status):
    """Route to specific transition handlers."""

    transitions = {
        ('pending', 'confirmed'): confirm_order,
        ('confirmed', 'shipped'): ship_order,
        ('shipped', 'delivered'): deliver_order,
        (None, 'pending'): create_order,
    }

    handler = transitions.get((old_status, new_status))
    if handler:
        handler(order)

def confirm_order(order):
    send_confirmation_email(order)
    charge_payment(order)

def ship_order(order):
    send_shipping_notification(order)
    create_shipping_label(order)

def deliver_order(order):
    send_delivery_confirmation(order)
    request_review(order)

def create_order(order):
    send_order_received_email(order)
```

### Async Handler (Django 3.1+)

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
import httpx

@receiver(post_save, sender=Article, dispatch_uid="article_saved_async")
def article_saved(sender, instance, created, **kwargs):
    """Handle Article save with async operations."""
    if created:
        # Call async function from sync context
        async_to_sync(notify_external_service)(instance)

async def notify_external_service(article):
    """Send notification to external API."""
    async with httpx.AsyncClient() as client:
        await client.post(
            'https://api.example.com/notify',
            json={'article_id': article.pk, 'title': article.title}
        )
```

### Handler with Retry Logic

```python
from django.db import transaction
from django.dispatch import receiver
from django.db.models.signals import post_save
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def send_to_external_api(data):
    """Send data to external API with retry."""
    import requests
    response = requests.post('https://api.example.com/data', json=data)
    response.raise_for_status()
    return response.json()

@receiver(post_save, sender=Order, dispatch_uid="order_external_sync")
def sync_order_to_external_system(sender, instance, created, **kwargs):
    """Sync order to external system with retry."""
    if created:
        transaction.on_commit(lambda: _sync_order(instance))

def _sync_order(order):
    """Helper to sync order (allows retry)."""
    try:
        send_to_external_api({
            'order_id': order.pk,
            'total': str(order.total),
            'customer': order.customer.email
        })
    except Exception as e:
        logger.error(f"Failed to sync order {order.pk} after retries: {e}")
        # Could send to dead letter queue here
```

## Error Handling

### Basic Error Handling

```python
import logging
from django.dispatch import receiver
from django.db.models.signals import post_save

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Order, dispatch_uid="order_saved")
def order_saved(sender, instance, created, **kwargs):
    """Handle Order save with error handling."""
    try:
        if created:
            send_confirmation_email(instance)
    except Exception as e:
        logger.error(
            f"Failed to send confirmation email for order {instance.pk}: {e}",
            exc_info=True
        )
        # Don't re-raise - let other handlers continue
```

### Error Handling with Fallback

```python
@receiver(post_save, sender=Article, dispatch_uid="article_notification")
def send_article_notification(sender, instance, created, **kwargs):
    """Send notification with fallback."""
    if not created:
        return

    try:
        # Try primary notification method
        send_push_notification(instance)
    except PushNotificationError as e:
        logger.warning(f"Push notification failed: {e}")

        try:
            # Fallback to email
            send_email_notification(instance)
        except EmailError as e:
            logger.error(f"All notification methods failed: {e}")
            # Queue for retry
            queue_notification_retry(instance)
```

### Error Handling with send_robust

Use `send_robust()` when sending signals to prevent one handler from breaking others:

```python
# When sending the signal
from myapp.signals import payment_completed

responses = payment_completed.send_robust(
    sender=Payment,
    payment=payment,
    amount=amount
)

# Log any errors
for receiver, response in responses:
    if isinstance(response, Exception):
        logger.error(
            f"Error in receiver {receiver}: {response}",
            exc_info=response
        )
```

## Performance Optimization

### Lazy Loading in Handlers

```python
@receiver(post_save, sender=Comment, dispatch_uid="comment_notification")
def notify_comment_author(sender, instance, created, **kwargs):
    """Notify article author of new comment."""
    if not created:
        return

    # BAD: N+1 query if called in loop
    # article = instance.article
    # author = article.author

    # GOOD: Use select_related if available
    if hasattr(instance, '_article_cache'):
        article = instance.article  # Already cached
    else:
        article = instance.article

    send_notification(article.author, instance)
```

### Batch Processing

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from collections import defaultdict
import threading

# Thread-local storage for batching
_batch_storage = threading.local()

def get_batch_storage():
    if not hasattr(_batch_storage, 'articles'):
        _batch_storage.articles = []
    return _batch_storage

@receiver(post_save, sender=Article, dispatch_uid="article_batch")
def batch_article_updates(sender, instance, created, **kwargs):
    """Batch article updates for efficiency."""
    storage = get_batch_storage()
    storage.articles.append(instance.pk)

    # Process batch at end of request (use middleware or on_commit)
    from django.db import transaction
    transaction.on_commit(lambda: process_article_batch())

def process_article_batch():
    """Process accumulated articles in batch."""
    storage = get_batch_storage()
    if not storage.articles:
        return

    article_ids = storage.articles
    storage.articles = []  # Clear batch

    # Bulk operation
    Article.objects.filter(pk__in=article_ids).update(
        last_processed=timezone.now()
    )
```

### Conditional Execution

```python
@receiver(post_save, sender=Article, dispatch_uid="article_search_update")
def update_search_index(sender, instance, created, **kwargs):
    """Update search index only when needed."""

    # Skip if not published
    if instance.status != 'published':
        return

    # Skip if only updating view_count
    update_fields = kwargs.get('update_fields')
    if update_fields and update_fields == {'view_count'}:
        return

    # Skip if title and content haven't changed
    if not created and update_fields:
        if not any(field in update_fields for field in ['title', 'content']):
            return

    # Now do the expensive operation
    update_index(instance)
```

### Offload to Task Queue

```python
from django.dispatch import receiver
from django.db.models.signals import post_save
from myapp.tasks import process_image_task

@receiver(post_save, sender=Image, dispatch_uid="image_processing")
def process_image(sender, instance, created, **kwargs):
    """Offload image processing to Celery."""
    if created:
        # Don't process in signal - use task queue
        process_image_task.delay(instance.pk)
```

## Debugging

### Logging Signal Execution

```python
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)

def log_signal_execution(func):
    """Decorator to log signal handler execution."""
    @wraps(func)
    def wrapper(sender, **kwargs):
        start_time = time.time()
        logger.info(f"Signal handler {func.__name__} started for {sender}")

        try:
            result = func(sender, **kwargs)
            elapsed = time.time() - start_time
            logger.info(
                f"Signal handler {func.__name__} completed in {elapsed:.2f}s"
            )
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"Signal handler {func.__name__} failed after {elapsed:.2f}s: {e}",
                exc_info=True
            )
            raise

    return wrapper

@receiver(post_save, sender=Article, dispatch_uid="article_saved")
@log_signal_execution
def article_saved(sender, instance, created, **kwargs):
    # Handler logic
    pass
```

### Debugging Signal Connections

```python
from django.db.models.signals import post_save

def debug_signal_receivers(signal, sender=None):
    """Print all receivers connected to a signal."""
    print(f"Receivers for {signal}:")

    for receiver in signal.receivers:
        receiver_func = receiver[1]()  # Weak reference
        if receiver_func:
            print(f"  - {receiver_func.__module__}.{receiver_func.__name__}")

            # Check if sender matches
            if sender and hasattr(receiver[0], 'sender'):
                if receiver[0].sender == sender:
                    print(f"    (matches sender: {sender})")

# Usage
debug_signal_receivers(post_save, sender=Article)
```

### Detecting Duplicate Connections

```python
from django.db.models.signals import post_save

def check_duplicate_receivers(signal):
    """Check for duplicate receiver connections."""
    receivers_by_func = {}

    for receiver in signal.receivers:
        receiver_func = receiver[1]()  # Weak reference
        if receiver_func:
            func_name = f"{receiver_func.__module__}.{receiver_func.__name__}"

            if func_name in receivers_by_func:
                print(f"WARNING: Duplicate receiver detected: {func_name}")
                print(f"  Registered {receivers_by_func[func_name] + 1} times")
                receivers_by_func[func_name] += 1
            else:
                receivers_by_func[func_name] = 1

# Usage in AppConfig.ready()
check_duplicate_receivers(post_save)
```

### Signal Execution Tracker

```python
class SignalTracker:
    """Track signal executions for debugging."""

    def __init__(self):
        self.executions = []

    def track(self, signal_name, sender, **kwargs):
        """Record a signal execution."""
        self.executions.append({
            'signal': signal_name,
            'sender': sender.__name__ if hasattr(sender, '__name__') else str(sender),
            'kwargs': {k: str(v) for k, v in kwargs.items()},
            'timestamp': timezone.now()
        })

    def print_executions(self):
        """Print all tracked executions."""
        for i, execution in enumerate(self.executions):
            print(f"{i}. {execution['signal']} - {execution['sender']}")
            print(f"   Time: {execution['timestamp']}")
            print(f"   Args: {execution['kwargs']}")

# Global tracker
signal_tracker = SignalTracker()

# Wrap handlers with tracking
@receiver(post_save, sender=Article, dispatch_uid="article_saved_tracked")
def article_saved(sender, instance, created, **kwargs):
    signal_tracker.track('post_save', sender, instance=instance, created=created)
    # Handler logic

# In tests or management command
signal_tracker.print_executions()
```

### Django Debug Toolbar Integration

```python
# Add to settings.py for signal debugging
INSTALLED_APPS = [
    # ...
    'debug_toolbar',
]

# In middleware
MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    # ...
]

# Custom panel for signal tracking
from debug_toolbar.panels import Panel

class SignalPanel(Panel):
    """Debug toolbar panel for signal tracking."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = []

    def record_signal(self, signal_name, sender):
        self.signals.append({
            'signal': signal_name,
            'sender': sender
        })

    # Register in debug toolbar settings
```

## Best Practices Summary

1. **Use @receiver decorator with dispatch_uid**
2. **Import signals in apps.py ready() method**
3. **Always accept **kwargs for forward compatibility**
4. **Keep handlers fast - offload heavy work to tasks**
5. **Use transaction.on_commit() for external operations**
6. **Handle errors gracefully - don't break request flow**
7. **Use logging for debugging**
8. **Document what each handler does**
9. **Test signal handlers thoroughly**
10. **Consider alternatives for performance-critical paths**
