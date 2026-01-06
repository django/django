# Signal Anti-Patterns and Alternatives

Critical guide to avoiding common signal pitfalls and choosing better alternatives.

## Table of Contents

- [The 5 Deadly Signal Anti-Patterns](#the-5-deadly-signal-anti-patterns)
- [When NOT to Use Signals](#when-not-to-use-signals)
- [Better Alternatives](#better-alternatives)
- [Refactoring Patterns](#refactoring-patterns)
- [Decision Matrix](#decision-matrix)

## The 5 Deadly Signal Anti-Patterns

### 1. Signal Recursion (Infinite Loops)

**The Problem:**

```python
# ANTI-PATTERN: Infinite recursion
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Article)
def update_view_count(sender, instance, **kwargs):
    instance.view_count += 1
    instance.save()  # Triggers post_save again → infinite loop!
```

**Why It's Bad:**
- Causes stack overflow errors
- Crashes your application
- Hard to debug in complex signal chains

**Detection:**
```python
# You'll see this error:
# RecursionError: maximum recursion depth exceeded
```

**Solutions:**

**Solution 1: Use QuerySet.update() (Best)**
```python
from django.db.models import F

@receiver(post_save, sender=Article)
def update_view_count(sender, instance, **kwargs):
    # update() doesn't trigger signals
    Article.objects.filter(pk=instance.pk).update(
        view_count=F('view_count') + 1
    )
```

**Solution 2: Check update_fields**
```python
@receiver(post_save, sender=Article)
def update_view_count(sender, instance, **kwargs):
    update_fields = kwargs.get('update_fields')

    # Skip if we're already updating view_count
    if update_fields and 'view_count' in update_fields:
        return

    instance.view_count += 1
    instance.save(update_fields=['view_count'])
```

**Solution 3: Use a flag**
```python
@receiver(post_save, sender=Article)
def update_view_count(sender, instance, **kwargs):
    # Skip if signal already processing this instance
    if getattr(instance, '_signal_processing', False):
        return

    instance._signal_processing = True
    try:
        instance.view_count += 1
        instance.save()
    finally:
        instance._signal_processing = False
```

**Best Alternative: Override save() method**
```python
class Article(models.Model):
    view_count = models.IntegerField(default=0)

    def increment_views(self):
        """Explicit method is better than hidden signal."""
        self.view_count += 1
        self.save(update_fields=['view_count'])

# In view:
article.increment_views()
```

---

### 2. Heavy Processing in Signals

**The Problem:**

```python
# ANTI-PATTERN: Slow operations block request
@receiver(post_save, sender=Order)
def process_order(sender, instance, created, **kwargs):
    if created:
        generate_invoice_pdf(instance)      # 2 seconds
        send_confirmation_email(instance)   # 1 second
        update_inventory(instance)          # 3 seconds
        notify_shipping(instance)           # 2 seconds
        # Total: 8 seconds blocking the request!
```

**Why It's Bad:**
- Blocks HTTP request/response cycle
- Poor user experience (slow page loads)
- Can cause timeouts
- Reduces throughput

**Detection:**
```python
# Slow requests, timeouts
# Users complaining about slow page loads
# High request duration in monitoring
```

**Solutions:**

**Solution 1: Use Task Queue (Best)**
```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from myapp.tasks import process_order_task

@receiver(post_save, sender=Order)
def queue_order_processing(sender, instance, created, **kwargs):
    if created:
        # Offload to Celery - instant return
        process_order_task.delay(instance.pk)

# myapp/tasks.py
from celery import shared_task

@shared_task
def process_order_task(order_id):
    order = Order.objects.get(pk=order_id)
    generate_invoice_pdf(order)
    send_confirmation_email(order)
    update_inventory(order)
    notify_shipping(order)
```

**Solution 2: Use transaction.on_commit() for I/O**
```python
from django.db import transaction

@receiver(post_save, sender=Order)
def process_order(sender, instance, created, **kwargs):
    if created:
        # Wait until transaction commits, then queue
        transaction.on_commit(
            lambda: process_order_task.delay(instance.pk)
        )
```

**Solution 3: Batch processing**
```python
@receiver(post_save, sender=Order)
def batch_order(sender, instance, created, **kwargs):
    if created:
        # Add to batch, process later in background
        redis_client.sadd('pending_orders', instance.pk)
        # Separate worker processes the batch
```

**Best Alternative: Service Layer**
```python
class OrderService:
    def create_order(self, **order_data):
        """Create order and handle all related processing."""
        order = Order.objects.create(**order_data)

        # Explicitly queue processing
        process_order_task.delay(order.pk)

        return order

# In view:
order = OrderService().create_order(
    customer=request.user,
    total=100
)
```

---

### 3. Database Queries in Loops (N+1 Problem)

**The Problem:**

```python
# ANTI-PATTERN: Signal fired in loop causes N+1 queries
@receiver(post_save, sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    # This query runs for EVERY item saved!
    order = instance.order
    order.total = order.items.aggregate(Sum('price'))['price__sum']
    order.save()  # Another query per item!

# In view:
for item_data in cart_items:
    OrderItem.objects.create(
        order=order,
        product=item_data['product'],
        quantity=item_data['quantity']
    )
    # Signal fires after each create → N queries!
```

**Why It's Bad:**
- Exponential query growth
- Severe performance degradation
- Database overload
- Increased latency

**Detection:**
```python
# Use Django Debug Toolbar or django-silk
# You'll see many duplicate queries

# Or enable query logging:
import logging
logging.getLogger('django.db.backends').setLevel(logging.DEBUG)
```

**Solutions:**

**Solution 1: Use bulk_create() (Best)**
```python
# Bulk operations don't trigger signals
items = [
    OrderItem(order=order, product=p['product'], quantity=p['quantity'])
    for p in cart_items
]
OrderItem.objects.bulk_create(items)

# Update total once
order.total = sum(item.product.price * item.quantity for item in items)
order.save()
```

**Solution 2: Disable signals during bulk operations**
```python
from django.db.models.signals import post_save

# Temporarily disconnect signal
post_save.disconnect(update_order_total, sender=OrderItem)

try:
    for item_data in cart_items:
        OrderItem.objects.create(...)
finally:
    # Reconnect signal
    post_save.connect(update_order_total, sender=OrderItem)

# Update total once
recalculate_order_total(order)
```

**Solution 3: Batch signal at end**
```python
@receiver(post_save, sender=OrderItem)
def schedule_order_update(sender, instance, **kwargs):
    # Schedule update for end of request
    transaction.on_commit(
        lambda: update_order_totals_task.delay(instance.order_id)
    )

# Celery task deduplicates if called multiple times
@shared_task
def update_order_totals_task(order_id):
    order = Order.objects.get(pk=order_id)
    order.total = order.items.aggregate(Sum('price'))['price__sum']
    order.save()
```

**Best Alternative: Manager Method**
```python
class OrderItemManager(models.Manager):
    def create_batch(self, order, items_data):
        """Create items and update order total in one go."""
        items = self.bulk_create([
            OrderItem(order=order, **item_data)
            for item_data in items_data
        ])

        # Update total once
        order.total = sum(
            item.product.price * item.quantity
            for item in items
        )
        order.save(update_fields=['total'])

        return items

# Usage:
OrderItem.objects.create_batch(order, cart_items)
```

---

### 4. Transaction Issues (Race Conditions)

**The Problem:**

```python
# ANTI-PATTERN: External operations before transaction commits
@receiver(post_save, sender=Payment)
def send_payment_receipt(sender, instance, created, **kwargs):
    if created:
        # Email sent even if transaction rolls back!
        send_email(
            to=instance.customer.email,
            subject='Payment Received',
            body=f'Your payment of ${instance.amount} was processed.'
        )

# In view:
try:
    with transaction.atomic():
        payment = Payment.objects.create(amount=100)
        # Email already sent!
        raise ValidationError("Invalid payment")
        # Transaction rolls back but email already sent!
except ValidationError:
    pass
```

**Why It's Bad:**
- Users receive incorrect notifications
- Data inconsistency
- External systems out of sync
- Hard to debug race conditions

**Real-World Example:**
```
1. User pays $100
2. Payment saved to database
3. Signal sends "Payment received" email ✉️
4. Credit card charge fails
5. Transaction rolls back
6. User has email but payment failed ❌
```

**Solutions:**

**Solution 1: Use transaction.on_commit() (Best)**
```python
from django.db import transaction

@receiver(post_save, sender=Payment)
def send_payment_receipt(sender, instance, created, **kwargs):
    if created:
        # Wait until transaction commits
        transaction.on_commit(
            lambda: send_email(
                to=instance.customer.email,
                subject='Payment Received',
                body=f'Your payment of ${instance.amount} was processed.'
            )
        )
```

**Solution 2: Task queue automatically waits**
```python
@receiver(post_save, sender=Payment)
def queue_receipt(sender, instance, created, **kwargs):
    if created:
        # Celery tasks queued on_commit by default
        send_receipt_task.delay(instance.pk)
```

**Solution 3: Explicit status field**
```python
class Payment(models.Model):
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )

@receiver(post_save, sender=Payment)
def send_receipt_on_completion(sender, instance, **kwargs):
    # Only send when explicitly completed
    if instance.status == 'completed':
        transaction.on_commit(
            lambda: send_email(...)
        )
```

**Best Alternative: Two-Phase Commit Pattern**
```python
class PaymentService:
    def process_payment(self, amount, token):
        """Two-phase payment processing."""
        # Phase 1: Create pending payment
        payment = Payment.objects.create(
            amount=amount,
            status='pending'
        )

        try:
            # Phase 2: Process with payment gateway
            result = payment_gateway.charge(token, amount)

            # Only mark completed if successful
            payment.status = 'completed'
            payment.transaction_id = result.id
            payment.save()

            # Now safe to send email
            send_email(...)

            return payment
        except PaymentError:
            payment.status = 'failed'
            payment.save()
            raise
```

---

### 5. Circular Signal Dependencies

**The Problem:**

```python
# ANTI-PATTERN: Circular signal chain
# user_signals.py
@receiver(post_save, sender=User)
def user_saved(sender, instance, **kwargs):
    if instance.profile is None:
        Profile.objects.create(user=instance)

# profile_signals.py
@receiver(post_save, sender=Profile)
def profile_saved(sender, instance, **kwargs):
    if not instance.user.email_verified:
        instance.user.email_verified = True
        instance.user.save()  # Triggers user_saved again!

# Result: User.save() → Profile.create() → User.save() → Profile.create()...
```

**Why It's Bad:**
- Infinite loops or recursion
- Unpredictable execution order
- Hard to debug and maintain
- Performance issues

**Visualization:**
```
User.save()
  └→ post_save signal
      └→ Profile.create()
          └→ post_save signal
              └→ User.save()
                  └→ post_save signal
                      └→ Profile.create()  [LOOP!]
```

**Detection:**
```python
# Enable signal debugging:
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use custom signal tracker:
from django.dispatch import receiver

original_send = Signal.send

def tracked_send(self, sender, **named):
    print(f"Signal: {self} from {sender}")
    return original_send(self, sender, **named)

Signal.send = tracked_send
```

**Solutions:**

**Solution 1: Break the chain with flags**
```python
@receiver(post_save, sender=User)
def user_saved(sender, instance, **kwargs):
    if instance.profile is None:
        profile = Profile(user=instance)
        profile._skip_signal = True  # Flag to skip handler
        profile.save()

@receiver(post_save, sender=Profile)
def profile_saved(sender, instance, **kwargs):
    if getattr(instance, '_skip_signal', False):
        return  # Skip if flagged

    if not instance.user.email_verified:
        user = instance.user
        user._skip_signal = True
        user.email_verified = True
        user.save()
```

**Solution 2: Use update_fields**
```python
@receiver(post_save, sender=Profile)
def profile_saved(sender, instance, **kwargs):
    update_fields = kwargs.get('update_fields')

    # Only process if specific fields changed
    if not update_fields or 'bio' not in update_fields:
        return

    # Update user with specific fields
    instance.user.profile_updated = True
    instance.user.save(update_fields=['profile_updated'])
```

**Solution 3: One-way signals with status fields**
```python
class User(models.Model):
    profile_created = models.BooleanField(default=False)

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created and not instance.profile_created:
        Profile.objects.create(user=instance)
        # Mark to avoid re-creation
        User.objects.filter(pk=instance.pk).update(
            profile_created=True
        )
```

**Best Alternative: Remove signals entirely**
```python
# Use model methods instead
class User(models.Model):
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            self.create_profile()

    def create_profile(self):
        """Explicit profile creation."""
        if not hasattr(self, 'profile'):
            Profile.objects.create(user=self)

# Or use post-creation in manager
class UserManager(models.Manager):
    def create_user(self, **kwargs):
        user = self.create(**kwargs)
        Profile.objects.create(user=user)
        return user
```

---

## When NOT to Use Signals

### 1. Single Receiver Only

**Don't Use Signal:**
```python
# AVOID: Only one receiver ever
@receiver(post_save, sender=Article)
def update_search_index(sender, instance, **kwargs):
    index_article(instance)
```

**Use Instead:**
```python
class Article(models.Model):
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        index_article(self)

# Or service method:
def publish_article(article):
    article.status = 'published'
    article.save()
    index_article(article)
```

### 2. Tightly Coupled Logic

**Don't Use Signal:**
```python
# AVOID: Logic is tightly coupled to model
@receiver(post_save, sender=Order)
def calculate_tax(sender, instance, **kwargs):
    instance.tax = instance.subtotal * 0.08
    instance.total = instance.subtotal + instance.tax
    instance.save()
```

**Use Instead:**
```python
class Order(models.Model):
    def calculate_totals(self):
        """Explicit, clear, testable."""
        self.tax = self.subtotal * Decimal('0.08')
        self.total = self.subtotal + self.tax

    def save(self, *args, **kwargs):
        self.calculate_totals()
        super().save(*args, **kwargs)
```

### 3. Performance Critical Paths

**Don't Use Signal:**
```python
# AVOID: Signals in hot path
@receiver(post_save, sender=PageView)
def track_analytics(sender, instance, **kwargs):
    # PageView saved thousands of times per second
    update_analytics(instance)
```

**Use Instead:**
```python
# Batch in Redis, process later
def record_page_view(page_id, user_id):
    redis_client.lpush('pageviews', json.dumps({
        'page_id': page_id,
        'user_id': user_id,
        'timestamp': time.time()
    }))

# Background worker processes batches
def process_pageview_batch():
    while True:
        batch = redis_client.lrange('pageviews', 0, 999)
        # Bulk process
        redis_client.ltrim('pageviews', 1000, -1)
```

### 4. Need Guaranteed Execution

**Don't Use Signal:**
```python
# AVOID: Signals can be disconnected
@receiver(post_save, sender=Payment)
def record_payment(sender, instance, **kwargs):
    # Critical: must always run
    create_audit_log(instance)
```

**Use Instead:**
```python
class PaymentService:
    @transaction.atomic
    def process_payment(self, amount):
        payment = Payment.objects.create(amount=amount)

        # Guaranteed to run
        AuditLog.objects.create(
            action='payment_created',
            payment=payment
        )

        return payment
```

### 5. Need Transactional Guarantees

**Don't Use Signal:**
```python
# AVOID: Complex transactional logic in signals
@receiver(post_save, sender=Order)
def process_order(sender, instance, created, **kwargs):
    charge_payment(instance)
    update_inventory(instance)
    send_to_warehouse(instance)
```

**Use Instead:**
```python
class OrderService:
    @transaction.atomic
    def create_order(self, order_data):
        order = Order.objects.create(**order_data)

        # Explicit transaction management
        try:
            self.charge_payment(order)
            self.update_inventory(order)
            self.send_to_warehouse(order)
        except Exception:
            # Transaction rolls back automatically
            raise

        return order
```

---

## Better Alternatives

### Alternative 1: Override save() Method

**When to use:** Logic is specific to one model

```python
class Article(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(blank=True)
    view_count = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        # Generate slug
        if not self.slug:
            self.slug = slugify(self.title)

        # Call parent
        super().save(*args, **kwargs)

        # Post-save operations
        cache.set(f'article_{self.pk}', self, 3600)
```

**Benefits:**
- Explicit and clear
- Easy to test
- No hidden behavior
- Better performance

### Alternative 2: Custom Manager Methods

**When to use:** Need controlled object creation

```python
class ArticleManager(models.Manager):
    def create_published(self, **kwargs):
        """Create and publish article."""
        kwargs['status'] = 'published'
        kwargs['published_at'] = timezone.now()

        article = self.create(**kwargs)

        # Post-creation actions
        notify_subscribers(article)
        update_search_index(article)

        return article

class Article(models.Model):
    objects = ArticleManager()

# Usage:
article = Article.objects.create_published(
    title='New Article',
    content='...'
)
```

**Benefits:**
- Explicit intent
- Reusable logic
- Easy to test
- Clear API

### Alternative 3: Service Layer

**When to use:** Complex business logic across models

```python
class OrderService:
    """Service for order operations."""

    @transaction.atomic
    def create_order(self, customer, items):
        """Create order with all related processing."""
        # Create order
        order = Order.objects.create(
            customer=customer,
            status='pending'
        )

        # Create items
        order_items = OrderItem.objects.bulk_create([
            OrderItem(order=order, **item)
            for item in items
        ])

        # Calculate totals
        order.total = sum(item.total for item in order_items)
        order.save()

        # Send notifications
        transaction.on_commit(
            lambda: send_order_confirmation(order.pk)
        )

        return order

    def confirm_order(self, order):
        """Confirm order and trigger fulfillment."""
        order.status = 'confirmed'
        order.confirmed_at = timezone.now()
        order.save()

        # Trigger fulfillment
        fulfill_order_task.delay(order.pk)

# Usage:
order_service = OrderService()
order = order_service.create_order(customer, cart_items)
```

**Benefits:**
- Clear business logic
- Easy to test
- Transaction control
- Explicit dependencies

### Alternative 4: Task Queue

**When to use:** Async operations, heavy processing

```python
# tasks.py
from celery import shared_task

@shared_task
def process_new_order(order_id):
    """Process new order asynchronously."""
    order = Order.objects.get(pk=order_id)

    generate_invoice(order)
    send_confirmation(order)
    update_inventory(order)
    notify_shipping(order)

# views.py
def create_order(request):
    order = Order.objects.create(...)

    # Queue processing
    process_new_order.delay(order.pk)

    return JsonResponse({'order_id': order.pk})
```

**Benefits:**
- Non-blocking
- Retriable
- Scalable
- Observable

### Alternative 5: Model Methods

**When to use:** Actions related to specific instances

```python
class Order(models.Model):
    status = models.CharField(max_length=20)

    def confirm(self):
        """Confirm the order."""
        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        self.save()

        # Related actions
        self.send_confirmation_email()
        self.notify_warehouse()

    def send_confirmation_email(self):
        """Send confirmation email."""
        send_mail(
            subject=f'Order #{self.pk} Confirmed',
            message='...',
            recipient_list=[self.customer.email]
        )

    def notify_warehouse(self):
        """Notify warehouse of new order."""
        warehouse_notification_task.delay(self.pk)

# Usage:
order.confirm()  # Explicit and clear!
```

**Benefits:**
- Self-documenting
- Explicit
- Testable
- Clear intent

---

## Refactoring Patterns

### Pattern 1: Signal → save() Override

**Before:**
```python
@receiver(pre_save, sender=Article)
def set_slug(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.title)
```

**After:**
```python
class Article(models.Model):
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
```

### Pattern 2: Signal → Manager Method

**Before:**
```python
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
```

**After:**
```python
class UserManager(models.Manager):
    def create_user(self, **kwargs):
        user = self.create(**kwargs)
        Profile.objects.create(user=user)
        return user
```

### Pattern 3: Signal → Service Layer

**Before:**
```python
@receiver(post_save, sender=Order)
def process_order(sender, instance, created, **kwargs):
    if created:
        send_email(instance)
        update_inventory(instance)
        notify_shipping(instance)
```

**After:**
```python
class OrderService:
    def create_order(self, **kwargs):
        order = Order.objects.create(**kwargs)
        self.send_confirmation(order)
        self.update_inventory(order)
        self.notify_shipping(order)
        return order
```

---

## Decision Matrix

| Scenario | Use Signal | Better Alternative |
|----------|-----------|-------------------|
| Single receiver | ❌ No | ✅ Override save() |
| Multiple apps need to react | ✅ Yes | - |
| Third-party app events | ✅ Yes | - |
| Tightly coupled to one model | ❌ No | ✅ Model method |
| Performance critical | ❌ No | ✅ Batch processing |
| Heavy processing | ❌ No | ✅ Task queue |
| Need transactional guarantees | ❌ No | ✅ Service layer |
| Audit logging | ❌ No | ✅ Middleware/decorator |
| Cache invalidation (cross-app) | ✅ Yes | - |
| Search index updates | ⚠️ Maybe | ✅ Task queue better |
| Creating related objects | ❌ No | ✅ Manager method |
| Sending notifications | ⚠️ Maybe | ✅ Task queue better |

## Summary

**Use signals for:**
- Cross-app communication
- Plugin/extension points
- Reacting to third-party app events
- Multiple independent receivers

**Don't use signals for:**
- Single receiver scenarios
- Tightly coupled logic
- Performance-critical paths
- Heavy processing
- Complex transactions

**Remember:**
- Signals add indirection and complexity
- Explicit is better than implicit
- Performance matters
- Test thoroughly
- Document dependencies

**Golden Rule:**
> "If you can achieve the same result without a signal, don't use a signal."
