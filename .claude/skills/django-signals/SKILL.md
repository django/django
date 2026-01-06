# Django Signals Skill

## Overview

Django signals provide a decoupled notification system that allows senders to notify receivers when actions occur. Signals enable cross-app communication and plugin architectures without tight coupling.

**When to use this skill:**
- Connecting to Django's built-in model lifecycle signals
- Creating custom signals for application-specific events
- Implementing cross-app communication
- Testing signal-driven behavior
- Debugging signal issues and avoiding anti-patterns

**Key concepts:**
- **Signals**: Notification dispatchers (e.g., `post_save`, `pre_delete`)
- **Senders**: Objects that send signals (usually model classes)
- **Receivers**: Functions/methods that handle signals
- **dispatch_uid**: Unique identifier to prevent duplicate connections

## Quick Start

The most common use case - connecting to model save signals:

```python
# myapp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from myapp.models import Article

@receiver(post_save, sender=Article, dispatch_uid="article_post_save")
def handle_article_save(sender, instance, created, **kwargs):
    if created:
        send_notification(instance)
    else:
        invalidate_cache(instance)

# myapp/apps.py
class MyAppConfig(AppConfig):
    name = 'myapp'

    def ready(self):
        import myapp.signals  # noqa: F401
```

## When to Use This Skill

**Use signals when:**
- Multiple apps need to react to the same event
- Working with third-party apps you can't modify
- Building plugin/extension systems
- Need cross-app decoupling

**Use alternatives when:**
- Only one receiver exists (use model methods)
- Logic is tightly coupled (override `save()`)
- Performance is critical (use task queues)
- Need transaction guarantees (use service layer)

See [reference/anti_patterns.md](reference/anti_patterns.md) for decision matrix.

## Core Workflows

### Workflow 1: Connect to Model Signals

**Steps:**

1. Create signals module:
```python
# myapp/signals.py
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction

@receiver(post_save, sender=Article, dispatch_uid="article_saved")
def article_saved(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: send_notification(instance))
    cache.set(f'article_{instance.pk}', instance, 3600)

@receiver(pre_delete, sender=Article, dispatch_uid="article_deleted")
def article_deleted(sender, instance, **kwargs):
    delete_related_files(instance)
    cache.delete(f'article_{instance.pk}')
```

2. Import in apps.py:
```python
class MyAppConfig(AppConfig):
    name = 'myapp'

    def ready(self):
        import myapp.signals  # noqa: F401
```

**Key points:**
- Use `dispatch_uid` to prevent duplicate connections
- Use `transaction.on_commit()` for external operations
- Check `created` flag in `post_save` to differentiate create vs update

See [reference/built_in_signals.md](reference/built_in_signals.md) for all available signals.

### Workflow 2: Create Custom Signals

**Steps:**

1. Define signal:
```python
# myapp/signals.py
from django.dispatch import Signal

payment_completed = Signal()
payment_completed.__doc__ = """
Sent when payment successfully processes.

Arguments:
    sender: Payment model class
    payment: Payment instance
    amount: Decimal amount paid
    transaction_id: String transaction ID
"""
```

2. Send signal:
```python
from myapp.signals import payment_completed

def process_payment(order, amount, token):
    payment = Payment.objects.create(order=order, amount=amount)

    payment_completed.send(
        sender=Payment,
        payment=payment,
        amount=amount,
        transaction_id=payment.transaction_id
    )
    return payment
```

3. Connect receivers:
```python
@receiver(payment_completed, dispatch_uid="send_receipt")
def send_receipt(sender, payment, amount, **kwargs):
    send_email_receipt(payment.customer, amount)

@receiver(payment_completed, dispatch_uid="update_analytics")
def track_payment(sender, payment, amount, **kwargs):
    analytics.track('payment', {'amount': amount})
```

**Best practices:**
- Use past tense names (`payment_completed`, not `payment_complete`)
- Document all arguments in docstring
- Always accept `**kwargs` for forward compatibility
- Use descriptive, specific names

See [reference/custom_signals.md](reference/custom_signals.md) for advanced patterns.

### Workflow 3: Avoid Signal Anti-Patterns

**Critical anti-patterns to avoid:**

**1. Signal Recursion:**
```python
# BAD: Infinite loop
@receiver(post_save, sender=Article)
def update_count(sender, instance, **kwargs):
    instance.view_count += 1
    instance.save()  # Triggers post_save again!

# GOOD: Use update()
@receiver(post_save, sender=Article)
def update_count(sender, instance, **kwargs):
    Article.objects.filter(pk=instance.pk).update(
        view_count=F('view_count') + 1
    )
```

**2. Heavy Processing:**
```python
# BAD: Blocks request
@receiver(post_save, sender=Order)
def process_order(sender, instance, created, **kwargs):
    if created:
        generate_pdf(instance)  # Slow!
        send_email(instance)    # Slow!

# GOOD: Use task queue
@receiver(post_save, sender=Order)
def queue_processing(sender, instance, created, **kwargs):
    if created:
        process_order_task.delay(instance.pk)
```

**3. Transaction Issues:**
```python
# BAD: Email sent before commit
@receiver(post_save, sender=Payment)
def send_receipt(sender, instance, **kwargs):
    send_email(instance)  # Sent even if transaction rolls back!

# GOOD: Wait for commit
@receiver(post_save, sender=Payment)
def send_receipt(sender, instance, **kwargs):
    transaction.on_commit(lambda: send_email(instance))
```

**4. N+1 Queries:**
```python
# BAD: Signal in loop
for item in items:
    OrderItem.objects.create(...)  # Signal fires each time!

# GOOD: Use bulk operations
OrderItem.objects.bulk_create(items)  # No signals
recalculate_totals(order)  # Update once
```

**5. Circular Dependencies:**
```python
# BAD: A triggers B triggers A
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)  # Triggers profile signal

@receiver(post_save, sender=Profile)
def update_user(sender, instance, **kwargs):
    instance.user.save()  # Triggers user signal!

# GOOD: Break the chain
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)
        # Don't trigger more signals
```

See [reference/anti_patterns.md](reference/anti_patterns.md) for detailed solutions and alternatives.

### Workflow 4: Test Signal Handlers

**Basic test pattern:**
```python
from django.test import TestCase
from myapp.models import Article

class SignalTests(TestCase):
    def test_notification_sent(self):
        """Test signal handler sends notification."""
        from django.core import mail

        Article.objects.create(title='Test')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('New article', mail.outbox[0].subject)
```

**Testing with mocks:**
```python
from unittest.mock import patch

class SignalTests(TestCase):
    @patch('myapp.signals.send_notification')
    def test_handler_called(self, mock_send):
        Article.objects.create(title='Test')
        mock_send.assert_called_once()
```

**Testing custom signals:**
```python
def test_custom_signal_sent(self):
    received = []

    def receiver(sender, **kwargs):
        received.append(kwargs)

    payment_completed.connect(receiver)
    try:
        process_payment(order, 100, 'token')
        self.assertEqual(len(received), 1)
    finally:
        payment_completed.disconnect(receiver)
```

**Transaction testing:**
```python
from django.test import TransactionTestCase

class TransactionSignalTests(TransactionTestCase):
    def test_on_commit_handler(self):
        """Use TransactionTestCase for on_commit handlers."""
        order = Order.objects.create(total=100)
        # Handler runs after commit
        self.assertEqual(len(mail.outbox), 1)
```

See [reference/testing.md](reference/testing.md) for comprehensive testing patterns.

### Workflow 5: Debug Signal Issues

**Common issues:**

1. **Signal not firing:** Check signal imported in `apps.py` `ready()`, app in `INSTALLED_APPS`, sender matches
2. **Multiple fires:** Add `dispatch_uid` to prevent duplicates
3. **Performance:** Run `scripts/analyze_signals.py`, move work to Celery, use `transaction.on_commit()`
4. **Test failures:** Use `TransactionTestCase` for `on_commit()` handlers, mock signals

See [reference/handlers.md#debugging](reference/handlers.md#debugging) for detailed debugging.

## When to Use Signals vs Alternatives

| Scenario | Use Signal? | Better Alternative |
|----------|-------------|-------------------|
| Multiple apps need to react | ✅ Yes | - |
| Third-party app events | ✅ Yes | - |
| Single receiver | ❌ No | Override `save()` |
| Tightly coupled logic | ❌ No | Model method |
| Heavy processing | ❌ No | Task queue |
| Performance critical | ❌ No | Batch processing |
| Need transaction guarantees | ❌ No | Service layer |

**Alternatives:**

**Override save():**
```python
class Article(models.Model):
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
        cache.set(f'article_{self.pk}', self)
```

**Service layer:**
```python
class OrderService:
    @transaction.atomic
    def create_order(self, customer, items):
        order = Order.objects.create(customer=customer)
        OrderItem.objects.bulk_create(items)
        send_confirmation(order)
        return order
```

**Task queue:**
```python
@shared_task
def process_order(order_id):
    order = Order.objects.get(pk=order_id)
    generate_invoice(order)
    send_email(order)
```

See [reference/anti_patterns.md](reference/anti_patterns.md) for detailed decision matrix.

## Scripts & Tools

### analyze_signals.py

Analyzes Django project for signal handlers and anti-patterns.

**Usage:**
```bash
python scripts/analyze_signals.py --project-dir /path/to/project
```

**Detects:**
- All signal handlers
- Missing `dispatch_uid`
- Recursion risks (save() in handlers)
- Transaction safety issues
- Heavy operations without `on_commit()`
- Duplicate handlers

### generate_signal.py

Generates boilerplate for custom signals.

**Usage:**
```bash
python scripts/generate_signal.py \
    --app myapp \
    --signal payment_completed \
    --args "payment,amount,transaction_id" \
    --sender Payment
```

**Generates:**
- Signal definition with documentation
- Example handler with `dispatch_uid`
- Example sender code
- Test template

## Performance Considerations

**Signal overhead:** ~0.1-1ms per signal dispatch

**Optimization strategies:**

1. **Use `transaction.on_commit()` for I/O:**
```python
@receiver(post_save, sender=Order)
def notify(sender, instance, **kwargs):
    transaction.on_commit(lambda: send_email(instance))
```

2. **Offload to task queue:**
```python
@receiver(post_save, sender=Image)
def process(sender, instance, **kwargs):
    process_image_task.delay(instance.pk)
```

3. **Avoid signals in hot paths:**
```python
# Bulk operations skip signals
Article.objects.bulk_create(articles)
Article.objects.filter(...).update(status='published')
```

4. **Conditional execution:**
```python
@receiver(post_save, sender=Article)
def update_index(sender, instance, **kwargs):
    if instance.status != 'published':
        return

    update_fields = kwargs.get('update_fields')
    if update_fields and 'title' not in update_fields:
        return

    reindex(instance)
```

## Anti-Patterns Summary

**Top 5 to avoid:**
1. **Signal recursion** - save() in post_save handler
2. **Heavy processing** - Slow operations blocking requests
3. **Transaction issues** - External calls before commit
4. **N+1 queries** - Signals in loops
5. **Circular dependencies** - Signal chains creating loops

See [reference/anti_patterns.md](reference/anti_patterns.md) for complete guide.

## Related Skills

- **django-models**: Model lifecycle and ORM operations
- **django-testing**: Testing strategies and patterns
- **django-admin**: Admin actions triggering signals

## Django Version Notes

- **Django 3.0+**: `providing_args` deprecated (use docstrings)
- **Django 3.1+**: Async signal support (`asend()`)
- **Django 4.0+**: Better transaction handling
- **Django 4.2+**: Performance improvements

## Reference Documentation

- [reference/built_in_signals.md](reference/built_in_signals.md) - All Django signals with examples
- [reference/custom_signals.md](reference/custom_signals.md) - Creating and documenting signals
- [reference/handlers.md](reference/handlers.md) - Handler patterns and organization
- [reference/testing.md](reference/testing.md) - Comprehensive testing guide
- [reference/anti_patterns.md](reference/anti_patterns.md) - What NOT to do (critical!)

## Troubleshooting

**"Signal handler not called"**
- Check signal imported in `apps.py` `ready()`
- Verify app in `INSTALLED_APPS`
- Ensure sender class matches exactly
- Check not using bulk operations

**"Signal called multiple times"**
- Add `dispatch_uid` to `@receiver` decorator
- Check `ready()` not called multiple times
- Verify no duplicate connections

**"Tests failing with signals"**
- Use `TransactionTestCase` for `on_commit()` handlers
- Mock signal handlers
- Disconnect signals in test setup

**"Performance issues"**
- Run `scripts/analyze_signals.py`
- Move work to Celery tasks
- Use `transaction.on_commit()` for I/O
- Consider alternatives to signals

For detailed debugging: [reference/handlers.md#debugging](reference/handlers.md#debugging)
