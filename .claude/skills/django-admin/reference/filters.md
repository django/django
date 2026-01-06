# Admin Filters Reference

Complete guide to Django admin filters, including built-in filters, custom filters, and facets.

## Table of Contents

1. [Built-in Filters](#built-in-filters)
2. [Custom SimpleListFilter](#custom-simplelistfilter)
3. [Custom FieldListFilter](#custom-fieldlistfilter)
4. [Facets (Django 6.0+)](#facets-django-60)
5. [Filter Optimization](#filter-optimization)
6. [Advanced Patterns](#advanced-patterns)

## Built-in Filters

### Basic Field Filters

Django automatically creates appropriate filters based on field type.

```python
class ProductAdmin(admin.ModelAdmin):
    list_filter = [
        'in_stock',      # BooleanField → Yes/No/All
        'category',      # ForeignKey → All instances
        'status',        # CharField with choices → Choice values
        'created_at',    # DateField → Date ranges
        'price',         # DecimalField → No filter (use custom)
    ]
```

### Boolean Field Filter

Automatically applied to BooleanField and NullBooleanField.

```python
# Filter sidebar shows:
# - All
# - Yes
# - No
# - Unknown (if null=True)

class ProductAdmin(admin.ModelAdmin):
    list_filter = ['in_stock', 'featured']
```

### ForeignKey Filter

Shows all related objects. Can be slow with many objects.

```python
class ProductAdmin(admin.ModelAdmin):
    list_filter = ['category']  # Shows all categories

# Sidebar shows:
# - All
# - Category 1
# - Category 2
# - ...
```

**For large datasets, use custom filter or autocomplete.**

### ManyToManyField Filter

Shows all related objects with "Any" option.

```python
class ArticleAdmin(admin.ModelAdmin):
    list_filter = ['tags']  # Shows all tags

# Shows: All, Tag1, Tag2, etc.
```

### ChoiceField Filter

Shows all choices defined in field.

```python
class Product(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

class ProductAdmin(admin.ModelAdmin):
    list_filter = ['status']

# Sidebar shows:
# - All
# - Draft
# - Published
# - Archived
```

### Date Field Filters

Automatic date range filters for DateField and DateTimeField.

```python
class ArticleAdmin(admin.ModelAdmin):
    list_filter = ['published_date']

# Sidebar shows:
# - Any date
# - Today
# - Past 7 days
# - This month
# - This year
```

**Specific date filters:**

```python
from django.contrib.admin import DateFieldListFilter

class ArticleAdmin(admin.ModelAdmin):
    list_filter = [
        ('published_date', DateFieldListFilter),  # Standard date ranges
    ]
```

### Related Field Filters

Filter by related object's fields.

```python
class OrderAdmin(admin.ModelAdmin):
    list_filter = [
        'customer__city',      # Filter by customer's city
        'items__product__category',  # Filter by product category
    ]
```

## Custom SimpleListFilter

Create custom filter logic with SimpleListFilter.

### Basic Custom Filter

```python
from django.contrib import admin

class PriceRangeFilter(admin.SimpleListFilter):
    title = 'price range'  # Filter title in sidebar
    parameter_name = 'price'  # URL parameter

    def lookups(self, request, model_admin):
        """Return list of (value, label) tuples"""
        return [
            ('0-50', 'Under $50'),
            ('50-100', '$50 - $100'),
            ('100-200', '$100 - $200'),
            ('200+', 'Over $200'),
        ]

    def queryset(self, request, queryset):
        """Return filtered queryset"""
        if self.value() == '0-50':
            return queryset.filter(price__lt=50)
        if self.value() == '50-100':
            return queryset.filter(price__gte=50, price__lt=100)
        if self.value() == '100-200':
            return queryset.filter(price__gte=100, price__lt=200)
        if self.value() == '200+':
            return queryset.filter(price__gte=200)

class ProductAdmin(admin.ModelAdmin):
    list_filter = [PriceRangeFilter, 'category']
```

### Dynamic Lookups

Generate filter options dynamically from database.

```python
class CategoryFilter(admin.SimpleListFilter):
    title = 'category'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        # Only show categories that have products
        categories = Category.objects.annotate(
            product_count=Count('products')
        ).filter(product_count__gt=0)

        return [(cat.id, f"{cat.name} ({cat.product_count})") for cat in categories]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(category_id=self.value())
```

### User-Specific Filters

Show different options based on current user.

```python
class AssignedToFilter(admin.SimpleListFilter):
    title = 'assigned to'
    parameter_name = 'assigned'

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            # Superusers see all staff
            users = User.objects.filter(is_staff=True)
            return [(user.id, user.get_full_name()) for user in users]
        else:
            # Regular users see only themselves
            return [(request.user.id, 'Me')]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(assigned_to_id=self.value())
```

### Date-Based Custom Filter

```python
from django.utils import timezone
from datetime import timedelta

class RecentActivityFilter(admin.SimpleListFilter):
    title = 'recent activity'
    parameter_name = 'activity'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('week', 'Past week'),
            ('month', 'Past month'),
            ('year', 'Past year'),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'today':
            start = now.replace(hour=0, minute=0, second=0)
            return queryset.filter(updated_at__gte=start)
        if self.value() == 'yesterday':
            start = now - timedelta(days=1)
            start = start.replace(hour=0, minute=0, second=0)
            end = now.replace(hour=0, minute=0, second=0)
            return queryset.filter(updated_at__gte=start, updated_at__lt=end)
        if self.value() == 'week':
            return queryset.filter(updated_at__gte=now - timedelta(days=7))
        if self.value() == 'month':
            return queryset.filter(updated_at__gte=now - timedelta(days=30))
        if self.value() == 'year':
            return queryset.filter(updated_at__gte=now - timedelta(days=365))
```

### Null/Empty Filter

Filter for null or empty values.

```python
class HasDescriptionFilter(admin.SimpleListFilter):
    title = 'has description'
    parameter_name = 'has_desc'

    def lookups(self, request, model_admin):
        return [
            ('yes', 'Yes'),
            ('no', 'No'),
            ('empty', 'Empty'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(description='').exclude(description__isnull=True)
        if self.value() == 'no':
            return queryset.filter(description__isnull=True)
        if self.value() == 'empty':
            return queryset.filter(description='')
```

### Annotation-Based Filter

Filter by computed values.

```python
from django.db.models import Count

class ReviewCountFilter(admin.SimpleListFilter):
    title = 'review count'
    parameter_name = 'reviews'

    def lookups(self, request, model_admin):
        return [
            ('none', 'No reviews'),
            ('1-5', '1-5 reviews'),
            ('5-10', '5-10 reviews'),
            ('10+', '10+ reviews'),
        ]

    def queryset(self, request, queryset):
        # Annotate if not already done
        if not hasattr(queryset.first(), '_review_count'):
            queryset = queryset.annotate(_review_count=Count('reviews'))

        if self.value() == 'none':
            return queryset.filter(_review_count=0)
        if self.value() == '1-5':
            return queryset.filter(_review_count__gte=1, _review_count__lte=5)
        if self.value() == '5-10':
            return queryset.filter(_review_count__gte=5, _review_count__lte=10)
        if self.value() == '10+':
            return queryset.filter(_review_count__gt=10)
```

## Custom FieldListFilter

Customize how specific fields are filtered.

### Basic FieldListFilter

```python
from django.contrib.admin import FieldListFilter

class StatusFieldListFilter(FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg = f"{field_path}__exact"
        self.lookup_val = params.get(self.lookup_kwarg)
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        return [self.lookup_kwarg]

    def choices(self, changelist):
        yield {
            'selected': self.lookup_val is None,
            'query_string': changelist.get_query_string(remove=[self.lookup_kwarg]),
            'display': 'All',
        }
        for choice_value, choice_label in [
            ('active', 'Active Only'),
            ('inactive', 'Inactive Only'),
        ]:
            yield {
                'selected': self.lookup_val == choice_value,
                'query_string': changelist.get_query_string({
                    self.lookup_kwarg: choice_value,
                }),
                'display': choice_label,
            }

class ProductAdmin(admin.ModelAdmin):
    list_filter = [
        ('status', StatusFieldListFilter),
    ]
```

### Dropdown Filter

More compact than sidebar list.

```python
from django.contrib.admin import ChoicesFieldListFilter

class ProductAdmin(admin.ModelAdmin):
    list_filter = [
        ('category', ChoicesFieldListFilter),  # Dropdown instead of list
    ]
```

### Related Dropdown Filter

```python
from django.contrib.admin import RelatedOnlyFieldListFilter

class OrderAdmin(admin.ModelAdmin):
    list_filter = [
        ('customer', RelatedOnlyFieldListFilter),  # Only customers with orders
    ]
```

### All Values Filter

Show all possible values for field.

```python
from django.contrib.admin import AllValuesFieldListFilter

class ProductAdmin(admin.ModelAdmin):
    list_filter = [
        ('manufacturer', AllValuesFieldListFilter),  # All manufacturers
    ]
```

### Empty Field Filter

Filter for empty/non-empty values.

```python
from django.contrib.admin import EmptyFieldListFilter

class ProductAdmin(admin.ModelAdmin):
    list_filter = [
        ('description', EmptyFieldListFilter),  # Has description / Empty
    ]
```

## Facets (Django 6.0+)

Show counts next to filter options.

### Enable Facets

```python
from django.contrib import admin

class ProductAdmin(admin.ModelAdmin):
    list_filter = ['category', 'in_stock', 'featured']
    show_facets = admin.ShowFacets.ALWAYS  # Always show counts

# Options:
# - admin.ShowFacets.ALWAYS: Always show
# - admin.ShowFacets.ALLOW: User can toggle
# - admin.ShowFacets.NEVER: Never show (default)
```

### Facets Display

```
Category
  All (1,234)
  Electronics (456)
  Books (321)
  Clothing (457)

In Stock
  All (1,234)
  Yes (890)
  No (344)
```

### Custom Filter with Facets

```python
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

    # Django 6.0+: Provide counts for facets
    def get_facets(self, request, queryset):
        from django.db.models import Count, Q
        counts = queryset.aggregate(
            under_50=Count('id', filter=Q(price__lt=50)),
            fifty_to_100=Count('id', filter=Q(price__gte=50, price__lt=100)),
            over_100=Count('id', filter=Q(price__gte=100)),
        )
        return {
            '0-50': counts['under_50'],
            '50-100': counts['fifty_to_100'],
            '100+': counts['over_100'],
        }
```

## Filter Optimization

### Optimize ForeignKey Filters

For large datasets, use select_related.

```python
class OrderAdmin(admin.ModelAdmin):
    list_filter = ['customer', 'status']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer')
```

### Limit Filter Options

Prevent showing thousands of filter options.

```python
class CustomerFilter(admin.SimpleListFilter):
    title = 'customer'
    parameter_name = 'customer'

    def lookups(self, request, model_admin):
        # Only show top 100 customers by order count
        customers = Customer.objects.annotate(
            order_count=Count('orders')
        ).order_by('-order_count')[:100]

        return [(c.id, f"{c.name} ({c.order_count} orders)") for c in customers]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(customer_id=self.value())
```

### Cache Filter Options

```python
from django.core.cache import cache

class CategoryFilter(admin.SimpleListFilter):
    title = 'category'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        cache_key = 'admin_category_filter_lookups'
        lookups = cache.get(cache_key)

        if lookups is None:
            categories = Category.objects.filter(active=True)
            lookups = [(c.id, c.name) for c in categories]
            cache.set(cache_key, lookups, 3600)  # Cache 1 hour

        return lookups

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(category_id=self.value())
```

### Use Autocomplete Instead

For very large datasets, use search instead of filters.

```python
class ProductAdmin(admin.ModelAdmin):
    search_fields = ['name', 'sku', 'category__name']
    # Instead of: list_filter = ['category']
```

## Advanced Patterns

### Hierarchical Filters

Filter with parent-child relationships.

```python
class CategoryFilter(admin.SimpleListFilter):
    title = 'category'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        categories = Category.objects.filter(parent__isnull=True)
        lookups = []

        for parent in categories:
            lookups.append((parent.id, parent.name))
            for child in parent.children.all():
                lookups.append((child.id, f"  → {child.name}"))

        return lookups

    def queryset(self, request, queryset):
        if self.value():
            category = Category.objects.get(id=self.value())
            # Include subcategories
            category_ids = [category.id] + list(
                category.get_descendants().values_list('id', flat=True)
            )
            return queryset.filter(category_id__in=category_ids)
```

### Multi-Select Filter

Allow selecting multiple filter values (requires custom template).

```python
class MultiSelectFilter(admin.SimpleListFilter):
    title = 'categories'
    parameter_name = 'categories'
    template = 'admin/multiselect_filter.html'

    def lookups(self, request, model_admin):
        return [(c.id, c.name) for c in Category.objects.all()]

    def queryset(self, request, queryset):
        values = request.GET.getlist(self.parameter_name)
        if values:
            return queryset.filter(category_id__in=values)

# Template: admin/multiselect_filter.html
# <ul>
#   {% for choice in choices %}
#   <li>
#     <input type="checkbox" name="{{ title }}" value="{{ choice.value }}"
#            {% if choice.selected %}checked{% endif %}>
#     {{ choice.display }}
#   </li>
#   {% endfor %}
# </ul>
```

### Combined Filters

Combine multiple conditions.

```python
class InventoryStatusFilter(admin.SimpleListFilter):
    title = 'inventory status'
    parameter_name = 'inventory'

    def lookups(self, request, model_admin):
        return [
            ('low', 'Low Stock (< 10)'),
            ('out', 'Out of Stock'),
            ('overstocked', 'Overstocked (> 100)'),
            ('discontinued', 'Discontinued & In Stock'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'low':
            return queryset.filter(stock__gt=0, stock__lt=10)
        if self.value() == 'out':
            return queryset.filter(stock=0)
        if self.value() == 'overstocked':
            return queryset.filter(stock__gt=100)
        if self.value() == 'discontinued':
            return queryset.filter(discontinued=True, stock__gt=0)
```

### Geographic Filters

Filter by location data.

```python
class RegionFilter(admin.SimpleListFilter):
    title = 'region'
    parameter_name = 'region'

    def lookups(self, request, model_admin):
        return [
            ('northeast', 'Northeast'),
            ('southeast', 'Southeast'),
            ('midwest', 'Midwest'),
            ('southwest', 'Southwest'),
            ('west', 'West'),
        ]

    def queryset(self, request, queryset):
        regions = {
            'northeast': ['NY', 'NJ', 'PA', 'CT', 'MA', 'VT', 'NH', 'ME', 'RI'],
            'southeast': ['FL', 'GA', 'NC', 'SC', 'VA', 'WV', 'KY', 'TN', 'AL', 'MS', 'AR', 'LA'],
            'midwest': ['OH', 'IN', 'IL', 'MI', 'WI', 'MN', 'IA', 'MO', 'ND', 'SD', 'NE', 'KS'],
            'southwest': ['TX', 'OK', 'NM', 'AZ'],
            'west': ['CA', 'NV', 'OR', 'WA', 'ID', 'MT', 'WY', 'CO', 'UT', 'AK', 'HI'],
        }

        if self.value() in regions:
            return queryset.filter(state__in=regions[self.value()])
```

## Complete Examples

### E-commerce Product Admin

```python
from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone

class StockLevelFilter(admin.SimpleListFilter):
    title = 'stock level'
    parameter_name = 'stock'

    def lookups(self, request, model_admin):
        return [
            ('in_stock', 'In Stock'),
            ('low', 'Low Stock (< 10)'),
            ('out', 'Out of Stock'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'in_stock':
            return queryset.filter(stock__gte=10)
        if self.value() == 'low':
            return queryset.filter(stock__gt=0, stock__lt=10)
        if self.value() == 'out':
            return queryset.filter(stock=0)

class ReviewQualityFilter(admin.SimpleListFilter):
    title = 'review quality'
    parameter_name = 'reviews'

    def lookups(self, request, model_admin):
        return [
            ('excellent', 'Excellent (4.5+)'),
            ('good', 'Good (3.5-4.5)'),
            ('poor', 'Poor (< 3.5)'),
            ('none', 'No reviews'),
        ]

    def queryset(self, request, queryset):
        queryset = queryset.annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )

        if self.value() == 'excellent':
            return queryset.filter(avg_rating__gte=4.5)
        if self.value() == 'good':
            return queryset.filter(avg_rating__gte=3.5, avg_rating__lt=4.5)
        if self.value() == 'poor':
            return queryset.filter(avg_rating__lt=3.5)
        if self.value() == 'none':
            return queryset.filter(review_count=0)

class ProductAdmin(admin.ModelAdmin):
    list_filter = [
        StockLevelFilter,
        ReviewQualityFilter,
        'category',
        ('created_at', admin.DateFieldListFilter),
    ]
    show_facets = admin.ShowFacets.ALWAYS

admin.site.register(Product, ProductAdmin)
```

### Blog Article Admin

```python
class PublishStatusFilter(admin.SimpleListFilter):
    title = 'publish status'
    parameter_name = 'publish_status'

    def lookups(self, request, model_admin):
        return [
            ('published', 'Published'),
            ('scheduled', 'Scheduled'),
            ('draft', 'Draft'),
            ('expired', 'Expired'),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()

        if self.value() == 'published':
            return queryset.filter(
                status='published',
                published_date__lte=now,
            ).filter(
                Q(expires_date__isnull=True) | Q(expires_date__gt=now)
            )
        if self.value() == 'scheduled':
            return queryset.filter(
                status='published',
                published_date__gt=now,
            )
        if self.value() == 'draft':
            return queryset.filter(status='draft')
        if self.value() == 'expired':
            return queryset.filter(
                status='published',
                expires_date__lte=now,
            )

class AuthorActivityFilter(admin.SimpleListFilter):
    title = 'author activity'
    parameter_name = 'author_activity'

    def lookups(self, request, model_admin):
        return [
            ('active', 'Active Authors (5+ articles)'),
            ('new', 'New Authors (1-4 articles)'),
            ('inactive', 'Inactive (no articles in 90 days)'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'active':
            active_authors = User.objects.annotate(
                article_count=Count('articles')
            ).filter(article_count__gte=5).values_list('id', flat=True)
            return queryset.filter(author_id__in=active_authors)

        if self.value() == 'new':
            new_authors = User.objects.annotate(
                article_count=Count('articles')
            ).filter(article_count__gte=1, article_count__lt=5).values_list('id', flat=True)
            return queryset.filter(author_id__in=new_authors)

        if self.value() == 'inactive':
            cutoff = timezone.now() - timedelta(days=90)
            inactive_authors = User.objects.filter(
                articles__created_at__lt=cutoff
            ).distinct().values_list('id', flat=True)
            return queryset.filter(author_id__in=inactive_authors)

class ArticleAdmin(admin.ModelAdmin):
    list_filter = [
        PublishStatusFilter,
        AuthorActivityFilter,
        'category',
        'featured',
        ('published_date', admin.DateFieldListFilter),
    ]
    show_facets = admin.ShowFacets.ALLOW

admin.site.register(Article, ArticleAdmin)
```

## Best Practices

1. **Performance**: Always optimize filter queries with select_related/prefetch_related
2. **Usability**: Limit options to reasonable numbers (< 100 items)
3. **Clarity**: Use descriptive titles and labels
4. **Context**: Show counts with facets when helpful
5. **Defaults**: Consider default filter values for common workflows
6. **Caching**: Cache expensive filter option lookups
7. **Testing**: Test filters with edge cases (empty data, null values)

## Troubleshooting

### Too Many Filter Options

**Problem**: ForeignKey filter shows thousands of items.

**Solution**: Use custom filter with limited lookups or autocomplete.

### Slow Filter Performance

**Problem**: Filter query takes too long.

**Solution**: Add database indexes, optimize queryset, or cache results.

### Missing Filter Counts (Facets)

**Problem**: Facets not showing counts.

**Solution**: Ensure Django 6.0+ and `show_facets = admin.ShowFacets.ALWAYS`.

### Filter Not Applied

**Problem**: Filter selected but queryset unchanged.

**Solution**: Check `parameter_name` matches between `lookups()` and `queryset()`.
