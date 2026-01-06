# Django Admin Skill

## Overview

This skill helps you work with Django's built-in admin interface. The Django admin provides a complete CRUD interface for your models with minimal code, but can be customized extensively for complex requirements.

**Use this skill when you need to:**
- Generate ModelAdmin classes from models
- Add custom admin actions (bulk operations)
- Implement object-level permissions
- Create custom admin views and dashboards
- Optimize admin queryset performance
- Customize filters, search, and display options
- Add inline editing for related models

## Quick Start

**Generate ModelAdmin from Model:**

```bash
python scripts/generate_admin.py path/to/models.py --model Product
```

This creates an optimized ModelAdmin with list_display, search_fields, filters, and query optimization.

## When to Use This Skill

**Use django-admin when:**
- Building internal admin interfaces (80% of Django projects)
- Need CRUD interface quickly
- Managing data for staff users
- Creating custom bulk operations
- Need per-object permissions

**Consider alternatives when:**
- Building public-facing UIs → Use django-views + django-templates
- Need complex multi-step workflows → Use django-forms + custom views
- API-only backends → Use DRF or django-views (JSON)

## Core Workflows

### Workflow 1: Generate ModelAdmin from Model

1. Run generator script:
   ```bash
   python scripts/generate_admin.py myapp/models.py --model Product
   ```

2. The script generates:
   - list_display with appropriate fields
   - search_fields for text fields
   - list_filter for categorical fields
   - list_select_related for ForeignKey optimization
   - Inlines for reverse relationships

3. Review and customize generated code
4. Add to admin.py and register

**See:** reference/modeladmin_options.md for all options

### Workflow 2: Add Custom Admin Actions

Define action function and add to ModelAdmin:

```python
from django.contrib import admin

@admin.action(description="Mark selected as published")
def make_published(modeladmin, request, queryset):
    updated = queryset.update(status='published')
    modeladmin.message_user(request, f"{updated} items published.")

class ArticleAdmin(admin.ModelAdmin):
    actions = [make_published]
```

**See:** reference/actions.md for actions with forms and confirmation

### Workflow 3: Implement Object-Level Permissions

Control which users can edit specific objects:

```python
class ArticleAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True  # Allow viewing list
        # Only author or superuser can edit
        return obj.author == request.user or request.user.is_superuser

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(author=request.user)
```

**See:** reference/permissions.md for advanced patterns

### Workflow 4: Create Custom Admin Views

Add custom pages to admin:

```python
from django.urls import path
from django.shortcuts import render

class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import/', self.admin_site.admin_view(self.import_view)),
        ]
        return custom_urls + urls

    def import_view(self, request):
        context = dict(
            self.admin_site.each_context(request),
            title="Import Products",
        )
        return render(request, "admin/product_import.html", context)
```

**See:** reference/custom_views.md for complete patterns

### Workflow 5: Optimize Admin Querysets

1. Run admin analyzer:
   ```bash
   python scripts/admin_analyzer.py myapp.admin
   ```

2. Review detected issues (N+1 queries, missing indexes)

3. Apply optimizations:
   ```python
   class OrderAdmin(admin.ModelAdmin):
       list_display = ['id', 'customer_name', 'total']
       list_select_related = ['customer', 'shipping_address']

       def get_queryset(self, request):
           qs = super().get_queryset(request)
           return qs.select_related('customer').prefetch_related('items')

       @admin.display(description='Customer')
       def customer_name(self, obj):
           return obj.customer.name  # No extra query
   ```

**See:** reference/modeladmin_options.md for optimization options

### Workflow 6: Add Advanced Filters

Create custom filters:

```python
from django.contrib import admin

class PriceRangeFilter(admin.SimpleListFilter):
    title = 'price range'
    parameter_name = 'price'

    def lookups(self, request, model_admin):
        return [
            ('0-50', 'Under $50'),
            ('50-100', '$50 - $100'),
            ('100+', 'Over $100'),
        ]

    def queryset(self, request, queryset):
        if self.value() == '0-50':
            return queryset.filter(price__lt=50)
        if self.value() == '50-100':
            return queryset.filter(price__gte=50, price__lt=100)
        if self.value() == '100+':
            return queryset.filter(price__gte=100)

class ProductAdmin(admin.ModelAdmin):
    list_filter = [PriceRangeFilter, 'category']
    show_facets = admin.ShowFacets.ALWAYS  # Django 6.0+: show counts
```

**See:** reference/filters.md for complete filter patterns

### Workflow 7: Configure Inline Editing

Edit related models on same page:

```python
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ['product', 'quantity', 'price']
    autocomplete_fields = ['product']

class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = ['id', 'customer', 'total', 'status']
```

**See:** reference/modeladmin_options.md for inline options

## Scripts & Tools

### generate_admin.py

Generate optimized ModelAdmin classes from models.

**Usage:**
```bash
# Generate for all models
python scripts/generate_admin.py myapp/models.py

# Specific model
python scripts/generate_admin.py myapp/models.py --model Product

# Output to file
python scripts/generate_admin.py myapp/models.py -o myapp/admin_generated.py
```

**Generates:** list_display, search_fields, filters, inlines, query optimization

### admin_analyzer.py

Detect performance issues and optimization opportunities.

**Usage:**
```bash
# Analyze all admin classes
python scripts/admin_analyzer.py myapp.admin

# Specific admin class
python scripts/admin_analyzer.py myapp.admin.ProductAdmin

# JSON output
python scripts/admin_analyzer.py myapp.admin --format json
```

**Detects:** N+1 queries, missing indexes, inefficient filters, optimization opportunities

## Common Patterns

### Pattern 1: Conditional Fieldsets

Show different fields based on state or user:

```python
class ArticleAdmin(admin.ModelAdmin):
    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Basic Info', {'fields': ['title', 'content', 'author']}),
        ]
        if obj and obj.status == 'published':
            fieldsets.append(
                ('Published Info', {'fields': ['published_date', 'view_count']})
            )
        if request.user.is_superuser:
            fieldsets.append(
                ('Admin Only', {'fields': ['featured'], 'classes': ['collapse']})
            )
        return fieldsets
```

### Pattern 2: Dynamic Autocomplete

Optimize autocomplete for large datasets:

```python
class ProductAdmin(admin.ModelAdmin):
    search_fields = ['name', 'sku']

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )
        # Custom search logic
        if search_term.startswith('#'):
            sku = search_term[1:]
            queryset |= self.model.objects.filter(sku__icontains=sku)
        # Optimize queryset
        queryset = queryset.select_related('category')
        return queryset, use_distinct
```

### Pattern 3: Export Action

```python
import csv
from django.http import HttpResponse

@admin.action(description="Export to CSV")
def export_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="export.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Email'])

    for obj in queryset:
        writer.writerow([obj.id, obj.name, obj.email])

    return response

class UserAdmin(admin.ModelAdmin):
    actions = [export_csv]
```

## Anti-Patterns

### ❌ Displaying Uncached Related Fields

```python
# Bad: N+1 query
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_email']
    def customer_email(self, obj):
        return obj.customer.email  # N+1 query!

# Good: Use list_select_related
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_email']
    list_select_related = ['customer']

    @admin.display(description='Customer Email', ordering='customer__email')
    def customer_email(self, obj):
        return obj.customer.email  # No extra query
```

### ❌ No Object-Level Permission Checks

```python
# Bad: Any staff user can edit any article
class ArticleAdmin(admin.ModelAdmin):
    pass

# Good: Check ownership
class ArticleAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        return obj.author == request.user or request.user.is_superuser
```

### ❌ Heavy Computation in list_display

```python
# Bad: Expensive aggregation on every row
class ProductAdmin(admin.ModelAdmin):
    def total_sales(self, obj):
        return obj.orders.aggregate(Sum('total'))['total__sum']

# Good: Annotate in get_queryset
class ProductAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_total_sales=Sum('orders__total'))

    @admin.display(description='Total Sales', ordering='_total_sales')
    def total_sales(self, obj):
        return obj._total_sales or 0
```

### ❌ Not Using Actions for Bulk Operations

```python
# Bad: Requiring users to edit objects one by one
class ArticleAdmin(admin.ModelAdmin):
    pass

# Good: Provide bulk actions
@admin.action(description="Publish selected articles")
def publish_articles(modeladmin, request, queryset):
    queryset.update(status='published')

class ArticleAdmin(admin.ModelAdmin):
    actions = [publish_articles]
```

### ❌ Ignoring Admin Security

```python
# Bad: No permission check
def export_users(modeladmin, request, queryset):
    return export_csv(queryset)

# Good: Check permissions
@admin.action(description="Export users", permissions=['export'])
def export_users(modeladmin, request, queryset):
    return export_csv(queryset)

class UserAdmin(admin.ModelAdmin):
    actions = [export_users]

    def has_export_permission(self, request):
        return request.user.has_perm('auth.export_user')
```

## Edge Cases & Gotchas

**Gotcha 1: Inline Ordering** - Inlines don't respect model Meta.ordering by default. Set explicitly:
```python
class OrderItemInline(admin.TabularInline):
    ordering = ['position']  # Explicit ordering
```

**Gotcha 2: Admin Site Registry** - Each ModelAdmin is bound to one AdminSite. For custom sites, create separate AdminSite instance.

**Gotcha 3: Actions on Empty Queryset** - Actions can be called with empty querysets. Check with `queryset.exists()`.

**Gotcha 4: Autocomplete Requires Search** - `autocomplete_fields` requires `search_fields` on related model's admin.

## Related Skills

- **django-models**: Model fields, relationships, constraints
- **django-forms**: ModelForms used internally by admin
- **django-views**: Custom admin views and overrides
- **django-templates**: Customizing admin templates
- **django-testing**: Testing admin classes and actions

## Django Version Notes

**Django 6.0+:** Facets in list_filter (show_facets), improved autocomplete, enhanced filter UI

**Django 5.0+:** Improved @admin.display decorator, better type hints, async admin views support

**Django 4.2 LTS:** Stable baseline, all core admin features available

**Django 3.2 LTS (EOL April 2024):** Missing modern decorators, use function attributes instead

## Reference Files

- **reference/modeladmin_options.md**: Complete list of all 100+ ModelAdmin options
- **reference/filters.md**: Built-in filters, custom filters, and facets
- **reference/actions.md**: Admin actions including actions with forms
- **reference/permissions.md**: Model and object-level permission patterns
- **reference/custom_views.md**: Creating custom admin pages and dashboards

## Complete Example

```python
from django.contrib import admin
from django.db.models import Count, Sum

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text']

@admin.action(description="Mark as featured")
def make_featured(modeladmin, request, queryset):
    updated = queryset.update(featured=True)
    modeladmin.message_user(request, f"{updated} products marked as featured.")

class ProductAdmin(admin.ModelAdmin):
    # Display
    list_display = ['name', 'sku', 'price', 'in_stock', 'review_count']
    list_display_links = ['name', 'sku']
    list_editable = ['price', 'in_stock']
    list_per_page = 50
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    # Search & Filter
    search_fields = ['name', 'sku', 'category__name']
    list_filter = ['in_stock', 'category', 'created_at']

    # Form
    fieldsets = [
        ('Basic Info', {'fields': ['name', 'sku', ('price', 'cost')]}),
        ('Details', {'fields': ['description', 'category', 'tags']}),
    ]
    filter_horizontal = ['tags']
    autocomplete_fields = ['category']
    prepopulated_fields = {'slug': ['name']}

    # Optimization
    list_select_related = ['category']

    # Actions & Inlines
    actions = [make_featured]
    inlines = [ProductImageInline]
    save_on_top = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _review_count=Count('reviews')
        ).prefetch_related('images')

    @admin.display(description='Reviews', ordering='_review_count')
    def review_count(self, obj):
        return obj._review_count

admin.site.register(Product, ProductAdmin)
```
