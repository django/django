# Admin Actions Reference

Complete guide to Django admin actions for bulk operations.

## Table of Contents

1. [Basic Actions](#basic-actions)
2. [Action Decorators](#action-decorators)
3. [Actions with Confirmation](#actions-with-confirmation)
4. [Actions with Forms](#actions-with-forms)
5. [Permissions](#permissions)
6. [Advanced Patterns](#advanced-patterns)
7. [Best Practices](#best-practices)

## Basic Actions

### Simple Action Function

Basic action that updates queryset.

```python
from django.contrib import admin

def make_published(modeladmin, request, queryset):
    """Mark selected items as published"""
    updated = queryset.update(status='published')
    modeladmin.message_user(request, f"{updated} items marked as published.")

class ArticleAdmin(admin.ModelAdmin):
    actions = [make_published]
```

### Action as Method

Define action as ModelAdmin method.

```python
class ArticleAdmin(admin.ModelAdmin):
    actions = ['make_published', 'make_draft']

    def make_published(self, request, queryset):
        updated = queryset.update(status='published')
        self.message_user(request, f"{updated} items published.")

    def make_draft(self, request, queryset):
        updated = queryset.update(status='draft')
        self.message_user(request, f"{updated} items marked as draft.")
```

### Action with Custom Description

```python
def make_published(modeladmin, request, queryset):
    queryset.update(status='published')

make_published.short_description = "Mark selected as published"

# Or use @admin.action decorator (Django 3.2+)
@admin.action(description="Mark selected as published")
def make_published(modeladmin, request, queryset):
    queryset.update(status='published')
```

## Action Decorators

### @admin.action Decorator (Django 3.2+)

Modern way to configure actions.

```python
from django.contrib import admin

@admin.action(description="Mark selected items as published")
def make_published(modeladmin, request, queryset):
    updated = queryset.update(status='published')
    modeladmin.message_user(request, f"{updated} items published.")

class ArticleAdmin(admin.ModelAdmin):
    actions = [make_published]
```

### Action with Permissions

Restrict action to users with specific permissions.

```python
@admin.action(
    description="Delete selected items permanently",
    permissions=['delete']  # Requires delete permission
)
def permanent_delete(modeladmin, request, queryset):
    queryset.delete()
    modeladmin.message_user(request, "Items deleted permanently.")

class ArticleAdmin(admin.ModelAdmin):
    actions = [permanent_delete]

    # Required permission check method
    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm('articles.delete_article')
```

### Custom Permission Check

```python
@admin.action(
    description="Export to CSV",
    permissions=['export']  # Custom permission
)
def export_csv(modeladmin, request, queryset):
    # Export logic
    pass

class ArticleAdmin(admin.ModelAdmin):
    actions = [export_csv]

    # Custom permission method (format: has_{permission}_permission)
    def has_export_permission(self, request):
        return request.user.groups.filter(name='Exporters').exists()
```

## Actions with Confirmation

### Intermediate Page with Confirmation

Show confirmation page before executing action.

```python
from django.contrib import admin
from django.shortcuts import render

@admin.action(description="Bulk delete selected items")
def bulk_delete(modeladmin, request, queryset):
    # POST means user confirmed
    if request.POST.get('post'):
        count = queryset.count()
        queryset.delete()
        modeladmin.message_user(
            request,
            f"Successfully deleted {count} items."
        )
        return

    # Show confirmation page
    context = {
        'title': 'Confirm bulk deletion',
        'queryset': queryset,
        'action': 'bulk_delete',
        'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
    }
    return render(request, 'admin/bulk_delete_confirmation.html', context)

class ArticleAdmin(admin.ModelAdmin):
    actions = [bulk_delete]
```

**Template (admin/bulk_delete_confirmation.html):**

```html
{% extends "admin/base_site.html" %}
{% load i18n %}

{% block content %}
<form method="post">
  {% csrf_token %}

  <p>Are you sure you want to delete {{ queryset.count }} items?</p>

  <ul>
    {% for obj in queryset %}
    <li>{{ obj }}</li>
    {% endfor %}
  </ul>

  {% for obj in queryset %}
  <input type="hidden" name="{{ action_checkbox_name }}" value="{{ obj.pk }}" />
  {% endfor %}

  <input type="hidden" name="action" value="{{ action }}" />
  <input type="hidden" name="post" value="yes" />

  <input type="submit" value="Yes, delete" />
  <a href="../">Cancel</a>
</form>
{% endblock %}
```

### Simple Confirmation

Use Django's messages framework for simple warnings.

```python
from django.contrib import messages

@admin.action(description="Archive selected items")
def archive_items(modeladmin, request, queryset):
    count = queryset.count()

    if count > 100:
        modeladmin.message_user(
            request,
            f"Cannot archive {count} items at once. Limit is 100.",
            level=messages.ERROR
        )
        return

    queryset.update(archived=True)
    modeladmin.message_user(
        request,
        f"Successfully archived {count} items.",
        level=messages.SUCCESS
    )
```

## Actions with Forms

### Action with Form Input

Collect additional input before processing.

```python
from django import forms
from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path

class BulkPriceUpdateForm(forms.Form):
    price_adjustment = forms.DecimalField(
        label="Price Adjustment (%)",
        help_text="Enter percentage to adjust prices (e.g., 10 for +10%, -5 for -5%)"
    )

class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'bulk-price-update/',
                self.admin_site.admin_view(self.bulk_price_update_view),
                name='products_product_bulk_price_update'
            ),
        ]
        return custom_urls + urls

    @admin.action(description="Bulk update prices")
    def bulk_update_prices(self, request, queryset):
        # Store selected IDs in session
        request.session['bulk_price_update_ids'] = list(
            queryset.values_list('pk', flat=True)
        )
        return redirect('admin:products_product_bulk_price_update')

    def bulk_price_update_view(self, request):
        product_ids = request.session.get('bulk_price_update_ids', [])
        products = Product.objects.filter(pk__in=product_ids)

        if request.method == 'POST':
            form = BulkPriceUpdateForm(request.POST)
            if form.is_valid():
                adjustment = form.cleaned_data['price_adjustment']

                for product in products:
                    product.price *= (1 + adjustment / 100)
                    product.save()

                self.message_user(
                    request,
                    f"Updated prices for {products.count()} products."
                )
                del request.session['bulk_price_update_ids']
                return redirect('..')
        else:
            form = BulkPriceUpdateForm()

        context = {
            **self.admin_site.each_context(request),
            'title': 'Bulk Price Update',
            'form': form,
            'products': products,
        }
        return render(request, 'admin/bulk_price_update.html', context)

    actions = [bulk_update_prices]
```

**Template (admin/bulk_price_update.html):**

```html
{% extends "admin/base_site.html" %}
{% load i18n %}

{% block content %}
<h1>Bulk Price Update</h1>

<p>Updating {{ products.count }} products:</p>

<form method="post">
  {% csrf_token %}
  {{ form.as_p }}

  <input type="submit" value="Update Prices" />
  <a href="..">Cancel</a>
</form>
{% endblock %}
```

### Action with Select Choices

```python
from django import forms
from django.contrib import admin
from django.shortcuts import render

class AssignCategoryForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=True,
        label="Select Category"
    )

@admin.action(description="Assign category to selected items")
def assign_category(modeladmin, request, queryset):
    if 'apply' in request.POST:
        form = AssignCategoryForm(request.POST)
        if form.is_valid():
            category = form.cleaned_data['category']
            updated = queryset.update(category=category)
            modeladmin.message_user(
                request,
                f"{updated} items assigned to {category}."
            )
            return
    else:
        form = AssignCategoryForm()

    context = {
        'title': 'Assign Category',
        'form': form,
        'queryset': queryset,
        'action': 'assign_category',
        'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
    }
    return render(request, 'admin/assign_category.html', context)

class ProductAdmin(admin.ModelAdmin):
    actions = [assign_category]
```

## Permissions

### Permission-Based Actions

Only show action to users with permission.

```python
@admin.action(description="Approve selected items", permissions=['change'])
def approve_items(modeladmin, request, queryset):
    queryset.update(approved=True)

class ArticleAdmin(admin.ModelAdmin):
    actions = [approve_items]

    # Permission check methods
    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('articles.change_article')
```

### Custom Permission Logic

```python
@admin.action(description="Publish selected articles", permissions=['publish'])
def publish_articles(modeladmin, request, queryset):
    queryset.update(status='published', published_at=timezone.now())

class ArticleAdmin(admin.ModelAdmin):
    actions = [publish_articles]

    def has_publish_permission(self, request):
        # Custom logic
        return (
            request.user.is_superuser or
            request.user.groups.filter(name='Publishers').exists()
        )
```

### Multiple Permissions

```python
@admin.action(
    description="Export and archive",
    permissions=['export', 'change']
)
def export_and_archive(modeladmin, request, queryset):
    # Export logic
    export_data(queryset)
    # Archive
    queryset.update(archived=True)

class ArticleAdmin(admin.ModelAdmin):
    actions = [export_and_archive]

    def has_export_permission(self, request):
        return request.user.has_perm('articles.export_article')

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('articles.change_article')
```

## Advanced Patterns

### Action with Progress Tracking

For long-running operations, use Celery or show progress.

```python
from django.contrib import admin
from django.http import JsonResponse
import time

@admin.action(description="Process selected items")
def process_items(modeladmin, request, queryset):
    total = queryset.count()
    processed = 0

    for item in queryset:
        # Process item
        item.process()
        processed += 1

        # Update progress (in real app, use Celery + websockets)
        if processed % 10 == 0:
            modeladmin.message_user(
                request,
                f"Processing: {processed}/{total}...",
                level=messages.INFO
            )

    modeladmin.message_user(
        request,
        f"Successfully processed {total} items."
    )
```

### Action with Error Handling

Handle errors gracefully and report issues.

```python
from django.contrib import messages
from django.db import transaction

@admin.action(description="Bulk process items")
def bulk_process(modeladmin, request, queryset):
    success_count = 0
    error_count = 0
    errors = []

    for item in queryset:
        try:
            with transaction.atomic():
                item.process()
                success_count += 1
        except Exception as e:
            error_count += 1
            errors.append(f"{item}: {str(e)}")

    # Report results
    if success_count:
        modeladmin.message_user(
            request,
            f"Successfully processed {success_count} items.",
            level=messages.SUCCESS
        )

    if error_count:
        error_message = f"Failed to process {error_count} items:\n"
        error_message += "\n".join(errors[:5])  # Show first 5 errors
        if len(errors) > 5:
            error_message += f"\n... and {len(errors) - 5} more"

        modeladmin.message_user(
            request,
            error_message,
            level=messages.ERROR
        )
```

### Export Actions

Export data in various formats.

```python
import csv
from django.http import HttpResponse

@admin.action(description="Export to CSV")
def export_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="export.csv"'

    writer = csv.writer(response)
    # Write headers
    writer.writerow(['ID', 'Name', 'Email', 'Created'])

    # Write data
    for obj in queryset:
        writer.writerow([
            obj.id,
            obj.name,
            obj.email,
            obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response

@admin.action(description="Export to JSON")
def export_json(modeladmin, request, queryset):
    from django.core.serializers import serialize
    from django.http import JsonResponse

    data = serialize('json', queryset)
    response = HttpResponse(data, content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="export.json"'
    return response

class UserAdmin(admin.ModelAdmin):
    actions = [export_csv, export_json]
```

### Action with Email Notification

```python
from django.core.mail import send_mass_mail

@admin.action(description="Send email to selected users")
def send_notification(modeladmin, request, queryset):
    if 'send' in request.POST:
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        emails = [
            (subject, message, 'noreply@example.com', [user.email])
            for user in queryset if user.email
        ]

        sent = send_mass_mail(emails, fail_silently=False)
        modeladmin.message_user(
            request,
            f"Sent {sent} emails successfully."
        )
        return

    context = {
        'title': 'Send Email',
        'queryset': queryset,
        'action': 'send_notification',
        'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
    }
    return render(request, 'admin/send_email.html', context)
```

### Batch Update with Validation

```python
@admin.action(description="Batch update with validation")
def batch_update(modeladmin, request, queryset):
    success = 0
    skipped = 0
    errors = []

    for obj in queryset:
        # Validate before update
        if not obj.can_be_updated():
            skipped += 1
            continue

        try:
            obj.status = 'updated'
            obj.full_clean()  # Run model validation
            obj.save()
            success += 1
        except ValidationError as e:
            errors.append(f"{obj}: {e}")

    # Report results
    if success:
        modeladmin.message_user(
            request,
            f"Updated {success} items.",
            level=messages.SUCCESS
        )

    if skipped:
        modeladmin.message_user(
            request,
            f"Skipped {skipped} items (validation failed).",
            level=messages.WARNING
        )

    if errors:
        modeladmin.message_user(
            request,
            f"Errors: {', '.join(errors[:3])}",
            level=messages.ERROR
        )
```

### Dynamic Action Generation

Create actions based on choices or states.

```python
def make_status_action(status_value, status_label):
    """Factory function to create status change actions"""
    @admin.action(description=f"Mark as {status_label}")
    def action(modeladmin, request, queryset):
        updated = queryset.update(status=status_value)
        modeladmin.message_user(
            request,
            f"{updated} items marked as {status_label}."
        )
    return action

class ArticleAdmin(admin.ModelAdmin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Generate actions for each status
        status_actions = []
        for value, label in Article.STATUS_CHOICES:
            action = make_status_action(value, label)
            action.__name__ = f'make_status_{value}'
            status_actions.append(action)

        self.actions = list(self.actions) + status_actions
```

## Best Practices

### 1. Always Provide Feedback

```python
@admin.action(description="Process items")
def process_items(modeladmin, request, queryset):
    count = queryset.count()

    # Process...
    queryset.update(processed=True)

    # Always tell user what happened
    modeladmin.message_user(
        request,
        f"Successfully processed {count} items."
    )
```

### 2. Handle Empty Querysets

```python
@admin.action(description="Process items")
def process_items(modeladmin, request, queryset):
    if not queryset.exists():
        modeladmin.message_user(
            request,
            "No items selected.",
            level=messages.WARNING
        )
        return

    # Process...
```

### 3. Use Transactions

```python
from django.db import transaction

@admin.action(description="Bulk update")
def bulk_update(modeladmin, request, queryset):
    with transaction.atomic():
        for obj in queryset:
            obj.process()
            obj.save()

    modeladmin.message_user(request, "Update complete.")
```

### 4. Optimize Queries

```python
@admin.action(description="Process with relations")
def process_with_relations(modeladmin, request, queryset):
    # Bad: N+1 queries
    # for obj in queryset:
    #     print(obj.category.name)

    # Good: Single query
    queryset = queryset.select_related('category')
    for obj in queryset:
        print(obj.category.name)
```

### 5. Validate Permissions

```python
@admin.action(description="Delete items", permissions=['delete'])
def delete_items(modeladmin, request, queryset):
    # Permission automatically checked by decorator
    queryset.delete()

class ArticleAdmin(admin.ModelAdmin):
    actions = [delete_items]

    def has_delete_permission(self, request, obj=None):
        # Custom validation
        return request.user.is_superuser
```

## Complete Examples

### Blog Article Actions

```python
from django.contrib import admin
from django.utils import timezone

@admin.action(description="Publish selected articles")
def publish_articles(modeladmin, request, queryset):
    queryset = queryset.filter(status='draft')
    updated = queryset.update(
        status='published',
        published_at=timezone.now()
    )
    modeladmin.message_user(
        request,
        f"Published {updated} articles."
    )

@admin.action(description="Schedule for tomorrow")
def schedule_tomorrow(modeladmin, request, queryset):
    tomorrow = timezone.now() + timezone.timedelta(days=1)
    tomorrow = tomorrow.replace(hour=9, minute=0, second=0)

    updated = queryset.update(
        status='scheduled',
        published_at=tomorrow
    )
    modeladmin.message_user(
        request,
        f"Scheduled {updated} articles for {tomorrow}."
    )

@admin.action(description="Feature on homepage", permissions=['change'])
def feature_articles(modeladmin, request, queryset):
    # Unfeature all current
    Article.objects.filter(featured=True).update(featured=False)

    # Feature selected
    updated = queryset.update(featured=True)
    modeladmin.message_user(
        request,
        f"Featured {updated} articles."
    )

class ArticleAdmin(admin.ModelAdmin):
    actions = [publish_articles, schedule_tomorrow, feature_articles]
    list_display = ['title', 'status', 'published_at', 'featured']
    list_filter = ['status', 'featured']
```

### E-commerce Product Actions

```python
from decimal import Decimal

@admin.action(description="Apply 10% discount")
def apply_discount(modeladmin, request, queryset):
    for product in queryset:
        product.price *= Decimal('0.9')
        product.save()

    modeladmin.message_user(
        request,
        f"Applied discount to {queryset.count()} products."
    )

@admin.action(description="Mark as out of stock")
def mark_out_of_stock(modeladmin, request, queryset):
    updated = queryset.update(in_stock=False, stock=0)
    modeladmin.message_user(
        request,
        f"Marked {updated} products as out of stock."
    )

@admin.action(description="Clone products")
def clone_products(modeladmin, request, queryset):
    cloned = 0
    for product in queryset:
        product.pk = None
        product.name = f"{product.name} (Copy)"
        product.sku = f"{product.sku}-COPY"
        product.save()
        cloned += 1

    modeladmin.message_user(
        request,
        f"Cloned {cloned} products."
    )

class ProductAdmin(admin.ModelAdmin):
    actions = [apply_discount, mark_out_of_stock, clone_products]
```

## Troubleshooting

### Action Not Appearing

**Problem**: Action doesn't show in admin.

**Solution**: Check:
- Action is in `actions` list
- User has required permissions
- Action is correctly defined as function or method

### Action Does Nothing

**Problem**: Action executes but no changes.

**Solution**: Check:
- Queryset is not empty
- Update/save is called
- No exceptions are silently caught

### Permission Denied

**Problem**: Action grayed out or not visible.

**Solution**: Check:
- User has required permission
- Permission check method exists (`has_{permission}_permission`)
- Permission name matches decorator

### Form Not Showing

**Problem**: Form in action not displayed.

**Solution**: Check:
- Template path is correct
- Context includes all required variables
- Form is rendered in template
