# Creating Custom Signals

Guide to defining and using custom signals in Django applications.

## Table of Contents

- [When to Create Custom Signals](#when-to-create-custom-signals)
- [Basic Signal Definition](#basic-signal-definition)
- [Providing Arguments](#providing-arguments)
- [Signal Naming Conventions](#signal-naming-conventions)
- [Sending Signals](#sending-signals)
- [Advanced Patterns](#advanced-patterns)
- [Documentation](#documentation)
- [Testing Custom Signals](#testing-custom-signals)

## When to Create Custom Signals

Create custom signals when:

1. **Multiple apps need to react to an event**
   - Example: Payment completed → send email, update analytics, notify shipping

2. **Event is business-domain specific**
   - Example: `order_shipped`, `user_subscribed`, `report_generated`

3. **You're building a plugin/extension system**
   - Example: Allow third-party apps to hook into your application's events

4. **Decoupling is more important than performance**
   - Signals have overhead; use direct calls if performance is critical

**Don't create custom signals when:**
- Only one receiver exists (use direct function call)
- Performance is critical (use message queue instead)
- Logic is tightly coupled to one model (override `save()` instead)
- You need guaranteed execution (signals can be disconnected)

## Basic Signal Definition

### Simple Signal

```python
# myapp/signals.py
from django.dispatch import Signal

# Create signal instance
payment_completed = Signal()
```

### Signal with Module Organization

```python
# myapp/signals/__init__.py
from django.dispatch import Signal

# User-related signals
user_registered = Signal()
user_activated = Signal()
user_deactivated = Signal()

# Order-related signals
order_placed = Signal()
order_shipped = Signal()
order_delivered = Signal()
order_cancelled = Signal()

# Payment-related signals
payment_initiated = Signal()
payment_completed = Signal()
payment_failed = Signal()
payment_refunded = Signal()
```

### Signal in Separate File

```python
# myapp/signals/payment_signals.py
from django.dispatch import Signal

payment_completed = Signal()
payment_failed = Signal()

# myapp/signals/__init__.py
from .payment_signals import payment_completed, payment_failed

__all__ = ['payment_completed', 'payment_failed']
```

## Providing Arguments

### Documenting Arguments (Django 3.0+)

The `providing_args` parameter is deprecated. Use docstrings instead:

```python
from django.dispatch import Signal

payment_completed = Signal()

# Document expected arguments
payment_completed.__doc__ = """
Signal sent when a payment is successfully processed.

Arguments:
    sender: The Payment model class
    payment: The Payment instance that was completed
    amount: Decimal amount that was paid
    transaction_id: String identifier from payment processor
    customer: User instance who made the payment (optional)
"""
```

### Comprehensive Documentation Pattern

```python
order_shipped = Signal()
order_shipped.__doc__ = """
Signal sent when an order has been shipped.

Sent from: OrderService.ship_order()

Arguments:
    sender (class): The Order model class
    order (Order): The order instance that was shipped
    tracking_number (str): Shipping tracking number
    carrier (str): Shipping carrier name (e.g., 'UPS', 'FedEx')
    estimated_delivery (datetime): Estimated delivery date and time
    shipping_address (Address): The address where order is being shipped

Example:
    from myapp.signals import order_shipped

    order_shipped.connect(send_shipping_notification)
    order_shipped.connect(update_inventory)

    # In your code:
    order_shipped.send(
        sender=Order,
        order=order,
        tracking_number='1Z999AA10123456784',
        carrier='UPS',
        estimated_delivery=datetime(2024, 1, 15, 17, 0),
        shipping_address=order.shipping_address
    )

See also: order_placed, order_delivered, order_cancelled
"""
```

## Signal Naming Conventions

### Past Tense for Completed Actions

```python
# GOOD: Past tense indicates action completed
user_registered = Signal()
payment_completed = Signal()
email_sent = Signal()
file_uploaded = Signal()
report_generated = Signal()

# AVOID: Present tense is ambiguous
user_register = Signal()
payment_complete = Signal()
email_send = Signal()
```

### Descriptive Names

```python
# GOOD: Clear and specific
subscription_expired = Signal()
trial_period_ending = Signal()
password_reset_requested = Signal()

# AVOID: Vague
subscription_changed = Signal()  # Changed how?
user_updated = Signal()  # What aspect updated?
```

### Namespace with App Name (Optional)

```python
# For large projects with many signals
from django.dispatch import Signal

# Billing app signals
billing_payment_completed = Signal()
billing_invoice_generated = Signal()
billing_subscription_cancelled = Signal()

# Notification app signals
notification_sent = Signal()
notification_failed = Signal()
```

## Sending Signals

### Basic Send

```python
# myapp/services.py
from myapp.signals import payment_completed
from myapp.models import Payment

def process_payment(order, amount, token):
    # Process payment
    payment = Payment.objects.create(
        order=order,
        amount=amount,
        status='completed',
        transaction_id='txn_abc123'
    )

    # Send signal
    payment_completed.send(
        sender=Payment,
        payment=payment,
        amount=amount,
        transaction_id=payment.transaction_id,
        customer=order.customer
    )

    return payment
```

### Send with Error Handling

```python
from myapp.signals import order_shipped
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

def ship_order(order, carrier, tracking_number):
    order.status = 'shipped'
    order.tracking_number = tracking_number
    order.save()

    # Send signal with error handling
    try:
        responses = order_shipped.send(
            sender=Order,
            order=order,
            tracking_number=tracking_number,
            carrier=carrier
        )

        # Check for errors in receivers
        for receiver, response in responses:
            if isinstance(response, Exception):
                logger.error(
                    f"Error in receiver {receiver}: {response}",
                    exc_info=response
                )
    except Exception as e:
        logger.error(f"Error sending order_shipped signal: {e}")
        # Don't let signal errors break the main flow
```

### Send with sender=None

```python
# Send without specific sender (less common)
generic_event = Signal()

generic_event.send(
    sender=None,  # No specific sender
    event_type='user_action',
    data={'action': 'clicked_button'}
)
```

### Conditional Sending

```python
def update_article(article, **fields):
    # Track which fields are changing
    changed_fields = []
    for field, value in fields.items():
        old_value = getattr(article, field)
        if old_value != value:
            changed_fields.append(field)
            setattr(article, field, value)

    article.save(update_fields=changed_fields)

    # Only send signal if title or content changed
    if 'title' in changed_fields or 'content' in changed_fields:
        article_updated.send(
            sender=Article,
            article=article,
            changed_fields=changed_fields
        )
```

## Advanced Patterns

### Signal Groups

Group related signals together:

```python
# myapp/signals/order_signals.py
from django.dispatch import Signal

class OrderSignals:
    """Container for all order-related signals."""

    placed = Signal()
    placed.__doc__ = "Sent when order is placed"

    confirmed = Signal()
    confirmed.__doc__ = "Sent when order is confirmed"

    shipped = Signal()
    shipped.__doc__ = "Sent when order is shipped"

    delivered = Signal()
    delivered.__doc__ = "Sent when order is delivered"

    cancelled = Signal()
    cancelled.__doc__ = "Sent when order is cancelled"

# Usage
from myapp.signals.order_signals import OrderSignals

OrderSignals.placed.send(sender=Order, order=order)
```

### Signal Factory

For dynamic signal creation:

```python
def create_status_signals(model_name, statuses):
    """Create signals for each status transition."""
    signals = {}

    for status in statuses:
        signal_name = f"{model_name}_{status}"
        signal = Signal()
        signal.__doc__ = f"Sent when {model_name} changes to {status} status"
        signals[signal_name] = signal

    return signals

# Create signals for order statuses
order_signals = create_status_signals('order', [
    'pending', 'confirmed', 'shipped', 'delivered', 'cancelled'
])
```

### Signal with send_robust

Use `send_robust()` to prevent one receiver's exception from stopping others:

```python
from myapp.signals import payment_completed

def process_payment(order, amount):
    payment = Payment.objects.create(order=order, amount=amount)

    # Use send_robust - continues even if receivers raise exceptions
    responses = payment_completed.send_robust(
        sender=Payment,
        payment=payment,
        amount=amount
    )

    # Log any errors
    for receiver, response in responses:
        if isinstance(response, Exception):
            logger.error(
                f"Error in receiver {receiver.__name__}: {response}",
                exc_info=response
            )

    return payment
```

### Async Signal Support (Django 3.1+)

```python
from django.dispatch import Signal

data_processed = Signal()

# Async sender
async def process_large_dataset(dataset_id):
    # Process data
    result = await process_data_async(dataset_id)

    # Send async signal
    await data_processed.asend(
        sender=Dataset,
        dataset_id=dataset_id,
        result=result
    )

# Async receiver
from django.dispatch import receiver

@receiver(data_processed)
async def handle_data_processed(sender, dataset_id, result, **kwargs):
    await send_notification_async(f"Dataset {dataset_id} processed")
```

## Documentation

### Signal Registry Documentation

Create a central registry:

```python
# myapp/signals/registry.py
"""
Signal Registry
===============

Central documentation for all signals in the application.

User Signals
------------
- user_registered: Sent when new user completes registration
- user_activated: Sent when user account is activated
- user_deactivated: Sent when user account is deactivated

Order Signals
-------------
- order_placed: Sent when customer places an order
- order_shipped: Sent when order is shipped
- order_delivered: Sent when order is delivered
- order_cancelled: Sent when order is cancelled

Payment Signals
---------------
- payment_completed: Sent when payment successfully processes
- payment_failed: Sent when payment fails
- payment_refunded: Sent when payment is refunded
"""

from django.dispatch import Signal

# Import all signals
from .user_signals import user_registered, user_activated, user_deactivated
from .order_signals import order_placed, order_shipped, order_delivered, order_cancelled
from .payment_signals import payment_completed, payment_failed, payment_refunded

# Export for easy importing
__all__ = [
    'user_registered', 'user_activated', 'user_deactivated',
    'order_placed', 'order_shipped', 'order_delivered', 'order_cancelled',
    'payment_completed', 'payment_failed', 'payment_refunded',
]
```

### README for Signals

```python
# myapp/signals/README.md
"""
# MyApp Signals

## Overview

This module defines custom signals for the MyApp application.

## Available Signals

### payment_completed

Sent when a payment is successfully processed.

**Location:** `myapp.signals.payment_completed`

**Arguments:**
- `sender`: Payment model class
- `payment`: Payment instance
- `amount`: Decimal amount paid
- `transaction_id`: String transaction ID

**Example:**
```python
from django.dispatch import receiver
from myapp.signals import payment_completed

@receiver(payment_completed)
def send_receipt(sender, payment, amount, **kwargs):
    send_email_receipt(payment.customer, amount)
```

**Connected Receivers:**
- `send_receipt` (myapp.signals.handlers)
- `update_analytics` (analytics.signals)
- `notify_accounting` (accounting.signals)

## Testing

See tests/test_signals.py for signal testing examples.

## Adding New Signals

1. Define signal in appropriate module (user_signals.py, order_signals.py, etc.)
2. Add comprehensive docstring with all arguments
3. Update this README
4. Add tests in tests/test_signals.py
5. Document in CHANGELOG.md
"""
```

## Testing Custom Signals

### Basic Test

```python
# tests/test_signals.py
from django.test import TestCase
from myapp.signals import payment_completed
from myapp.models import Payment

class PaymentSignalTests(TestCase):
    def test_payment_completed_signal_sent(self):
        """Test that payment_completed signal is sent."""
        received = []

        def test_receiver(sender, payment, amount, **kwargs):
            received.append({
                'payment': payment,
                'amount': amount,
                'transaction_id': kwargs.get('transaction_id')
            })

        # Connect test receiver
        payment_completed.connect(test_receiver)

        try:
            # Create payment (should send signal)
            from myapp.services import process_payment
            from myapp.models import Order

            order = Order.objects.create(total=100)
            payment = process_payment(order, 100, 'tok_test')

            # Verify signal was sent
            self.assertEqual(len(received), 1)
            self.assertEqual(received[0]['payment'], payment)
            self.assertEqual(received[0]['amount'], 100)
        finally:
            # Disconnect test receiver
            payment_completed.disconnect(test_receiver)
```

### Testing Signal Arguments

```python
class SignalArgumentTests(TestCase):
    def test_payment_completed_arguments(self):
        """Test payment_completed signal sends correct arguments."""
        def verify_arguments(sender, payment, amount, transaction_id, **kwargs):
            self.assertEqual(sender, Payment)
            self.assertIsInstance(payment, Payment)
            self.assertIsInstance(amount, Decimal)
            self.assertIsInstance(transaction_id, str)
            self.assertIn('customer', kwargs)

        payment_completed.connect(verify_arguments)

        try:
            order = Order.objects.create(total=100)
            process_payment(order, 100, 'tok_test')
        finally:
            payment_completed.disconnect(verify_arguments)
```

### Testing with Mock

```python
from unittest.mock import patch, call

class SignalMockTests(TestCase):
    @patch('myapp.signals.payment_completed.send')
    def test_service_sends_signal(self, mock_signal):
        """Test that service sends payment_completed signal."""
        order = Order.objects.create(total=100)
        payment = process_payment(order, 100, 'tok_test')

        # Verify signal was sent with correct arguments
        mock_signal.assert_called_once()
        call_kwargs = mock_signal.call_args[1]

        self.assertEqual(call_kwargs['sender'], Payment)
        self.assertEqual(call_kwargs['payment'], payment)
        self.assertEqual(call_kwargs['amount'], 100)
```

### Testing Signal Handlers

```python
class SignalHandlerTests(TestCase):
    def test_receipt_sent_on_payment_completed(self):
        """Test that receipt email is sent when payment completes."""
        from django.core import mail

        order = Order.objects.create(
            total=100,
            customer_email='test@example.com'
        )

        process_payment(order, 100, 'tok_test')

        # Verify email sent by signal handler
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Receipt', mail.outbox[0].subject)
        self.assertIn('test@example.com', mail.outbox[0].to)
```

## Best Practices

### 1. Signal Definition Location

```python
# GOOD: Define in signals.py or signals/ module
myapp/
├── signals.py          # All signals for small apps
├── handlers.py         # All receivers
└── models.py

# GOOD: Organize by domain for larger apps
myapp/
├── signals/
│   ├── __init__.py     # Export all signals
│   ├── user_signals.py
│   ├── order_signals.py
│   └── payment_signals.py
├── handlers/
│   ├── __init__.py
│   ├── user_handlers.py
│   ├── order_handlers.py
│   └── payment_handlers.py
└── models.py
```

### 2. Always Document Arguments

```python
# GOOD
payment_completed = Signal()
payment_completed.__doc__ = """
Signal sent when payment completes.

Arguments:
    sender: Payment class
    payment: Payment instance
    amount: Decimal amount
"""

# BAD: No documentation
payment_completed = Signal()
```

### 3. Use Descriptive Names

```python
# GOOD
user_subscription_renewed = Signal()
password_reset_token_generated = Signal()
invoice_payment_overdue = Signal()

# BAD: Too generic
user_updated = Signal()
event_occurred = Signal()
data_changed = Signal()
```

### 4. Keep Sender Consistent

```python
# GOOD: Always use model class as sender
payment_completed.send(sender=Payment, payment=payment)

# AVOID: Inconsistent senders
payment_completed.send(sender=self, payment=payment)
payment_completed.send(sender='Payment', payment=payment)
```

### 5. Version Your Signals

```python
# For breaking changes, version your signals
payment_completed_v2 = Signal()
payment_completed_v2.__doc__ = """
Version 2 of payment_completed signal.

Changes from v1:
- Added 'payment_method' argument
- Changed 'transaction_id' to 'external_transaction_id'

Deprecated: payment_completed (v1) - will be removed in version 3.0
"""
```

## Migration Guide

### Replacing Built-in Signals with Custom Signals

```python
# Old: Using post_save
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Order)
def handle_order_save(sender, instance, created, **kwargs):
    if created and instance.status == 'confirmed':
        send_confirmation(instance)

# New: Using custom signal (better)
from django.dispatch import Signal

order_confirmed = Signal()

# In model or service
def confirm_order(order):
    order.status = 'confirmed'
    order.save()
    order_confirmed.send(sender=Order, order=order)

# Handler
@receiver(order_confirmed)
def handle_order_confirmed(sender, order, **kwargs):
    send_confirmation(order)
```

**Benefits:**
- More explicit intent
- Decouples from model save
- Can send from multiple locations
- Clearer semantics

## Common Patterns

### Event Sourcing Pattern

```python
# Define event signals
from django.dispatch import Signal

class OrderEvents:
    created = Signal()
    confirmed = Signal()
    paid = Signal()
    shipped = Signal()
    delivered = Signal()
    cancelled = Signal()

# Log all events
@receiver(OrderEvents.created)
@receiver(OrderEvents.confirmed)
@receiver(OrderEvents.paid)
@receiver(OrderEvents.shipped)
@receiver(OrderEvents.delivered)
@receiver(OrderEvents.cancelled)
def log_order_event(sender, order, **kwargs):
    event_type = None
    for attr_name in dir(OrderEvents):
        attr = getattr(OrderEvents, attr_name)
        if isinstance(attr, Signal) and attr == sender:
            event_type = attr_name
            break

    OrderEvent.objects.create(
        order=order,
        event_type=event_type,
        timestamp=timezone.now()
    )
```

### Notification Pattern

```python
# Generic notification signal
notification_requested = Signal()
notification_requested.__doc__ = """
Arguments:
    sender: Model class
    user: User to notify
    notification_type: String type identifier
    context: Dict of context data
"""

# Send from anywhere
notification_requested.send(
    sender=Order,
    user=order.customer,
    notification_type='order_shipped',
    context={'order': order, 'tracking': tracking_number}
)

# Single handler routes to all channels
@receiver(notification_requested)
def send_notification(sender, user, notification_type, context, **kwargs):
    send_email_notification(user, notification_type, context)
    send_push_notification(user, notification_type, context)
    create_in_app_notification(user, notification_type, context)
```

This pattern centralizes notification logic while allowing any part of the system to trigger notifications.
