# ModelAdmin Options Reference

Complete reference for all Django ModelAdmin configuration options.

## Table of Contents

1. [Display Options](#display-options)
2. [Form Options](#form-options)
3. [Query Optimization](#query-optimization)
4. [Filtering and Search](#filtering-and-search)
5. [Actions](#actions)
6. [Inlines](#inlines)
7. [Permissions](#permissions)
8. [Customization Methods](#customization-methods)
9. [Admin Site Options](#admin-site-options)

## Display Options

### list_display

Controls which fields appear in the changelist (list view).

```python
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'in_stock', 'category', 'get_image_preview']

    @admin.display(description='Preview')
    def get_image_preview(self, obj):
        return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
```

**Options:**
- Field names: `'name'`, `'price'`
- Related fields: `'category__name'` (read-only)
- Methods: `'get_total'`, decorated with `@admin.display`
- Model methods: `'__str__'`, `'get_absolute_url'`

**@admin.display decorator attributes:**
- `description`: Column header text
- `ordering`: Field(s) to order by
- `boolean`: Display as boolean icon
- `empty_value`: Text for None values

```python
@admin.display(description='Total', ordering='price')
def get_total(self, obj):
    return f"${obj.price * obj.quantity}"
```

### list_display_links

Fields that link to the change form. Defaults to first field.

```python
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'category']
    list_display_links = ['sku', 'name']  # Both link to edit page
```

Set to `None` to remove all links (useful for readonly lists):
```python
list_display_links = None
```

### list_editable

Fields editable directly in changelist.

```python
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'in_stock']
    list_editable = ['price', 'in_stock']  # Edit without opening form
```

**Restrictions:**
- Cannot include fields in list_display_links
- Cannot be the first field (must have a link field)
- Field must be in list_display

### list_per_page

Number of items per page. Default: 100.

```python
class ProductAdmin(admin.ModelAdmin):
    list_per_page = 25
```

### list_max_show_all

Maximum items for "Show all" link. Default: 200.

```python
class ProductAdmin(admin.ModelAdmin):
    list_max_show_all = 500  # Show "all" link if under 500 items
```

### ordering

Default ordering for changelist.

```python
class ProductAdmin(admin.ModelAdmin):
    ordering = ['-created_at', 'name']  # Newest first, then by name
```

### sortable_by

Fields that can be sorted. By default, all fields in list_display.

```python
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'computed_field']
    sortable_by = ['name', 'price']  # computed_field not sortable
```

### date_hierarchy

Drill-down navigation by date field.

```python
class ArticleAdmin(admin.ModelAdmin):
    date_hierarchy = 'published_date'  # Adds year/month/day drill-down
```

### empty_value_display

Default text for empty/None values.

```python
class ProductAdmin(admin.ModelAdmin):
    empty_value_display = '-empty-'
```

Per-field override:
```python
@admin.display(description='Price', empty_value='???')
def display_price(self, obj):
    return obj.price
```

### show_facets

Django 6.0+: Show filter counts.

```python
from django.contrib import admin

class ProductAdmin(admin.ModelAdmin):
    show_facets = admin.ShowFacets.ALWAYS  # Show counts
    # Options: ALWAYS, ALLOW (user toggles), NEVER
```

## Form Options

### fields

Fields to display in the form. Simple alternative to fieldsets.

```python
class ProductAdmin(admin.ModelAdmin):
    fields = ['name', 'sku', 'price', 'category', 'description']
```

Inline fields (same row):
```python
fields = ['name', ('price', 'discount')]  # price and discount side-by-side
```

### exclude

Fields to exclude from form. Cannot use with `fields` or `fieldsets`.

```python
class ProductAdmin(admin.ModelAdmin):
    exclude = ['internal_notes', 'legacy_id']
```

### fieldsets

Organize form into sections with optional collapse/description.

```python
class ProductAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'sku', 'price'],
        }),
        ('Details', {
            'fields': ['description', 'category', 'tags'],
            'classes': ['collapse'],  # Collapsed by default
            'description': 'Additional product information',
        }),
        ('Advanced', {
            'fields': ['weight', 'dimensions', 'manufacturer'],
            'classes': ['collapse', 'wide'],  # Wide and collapsed
        }),
    ]
```

**Field options in fieldsets:**
- `fields`: List of fields (use tuples for same row)
- `classes`: CSS classes (`collapse`, `wide`, `extrapretty`)
- `description`: Help text for section

### readonly_fields

Fields displayed but not editable.

```python
class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ['order_number', 'created_at', 'total_display']

    @admin.display(description='Total')
    def total_display(self, obj):
        return f"${obj.total}"
```

### form

Custom ModelForm class.

```python
from django import forms

class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 0:
            raise forms.ValidationError("Price cannot be negative")
        return price

class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
```

### formfield_overrides

Override widget for specific field types.

```python
from django import forms
from django.db import models

class ProductAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': forms.Textarea(attrs={'rows': 4})},
        models.CharField: {'widget': forms.TextInput(attrs={'size': 50})},
    }
```

### prepopulated_fields

Auto-fill fields based on other fields (e.g., slug from title).

```python
class ArticleAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ['title']}  # Slug from title
```

### radio_fields

Display ForeignKey/choice fields as radio buttons.

```python
from django.contrib import admin

class ProductAdmin(admin.ModelAdmin):
    radio_fields = {
        'category': admin.VERTICAL,
        'status': admin.HORIZONTAL,
    }
```

### autocomplete_fields

Use autocomplete widget for ForeignKey/ManyToMany.

```python
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    autocomplete_fields = ['product']  # Autocomplete search

class ProductAdmin(admin.ModelAdmin):
    search_fields = ['name', 'sku']  # Required for autocomplete
```

### raw_id_fields

Display ForeignKey/ManyToMany as raw ID input with lookup icon.

```python
class OrderAdmin(admin.ModelAdmin):
    raw_id_fields = ['customer', 'shipping_address']
```

### filter_horizontal / filter_vertical

Enhanced widget for ManyToMany fields.

```python
class ArticleAdmin(admin.ModelAdmin):
    filter_horizontal = ['tags', 'categories']  # Horizontal layout
    # OR
    filter_vertical = ['tags']  # Vertical layout
```

### save_as

Show "Save as new" button to duplicate objects.

```python
class ProductAdmin(admin.ModelAdmin):
    save_as = True  # Adds "Save as new" button
```

### save_as_continue

After "Save as new", continue editing new object.

```python
class ProductAdmin(admin.ModelAdmin):
    save_as = True
    save_as_continue = True  # Stay on edit page after save as new
```

### save_on_top

Show save buttons at top and bottom.

```python
class ProductAdmin(admin.ModelAdmin):
    save_on_top = True  # Duplicate buttons at top
```

### view_on_site

Add "View on site" button.

```python
class ArticleAdmin(admin.ModelAdmin):
    # Option 1: Use model's get_absolute_url()
    view_on_site = True

    # Option 2: Custom method
    def view_on_site(self, obj):
        return f"https://example.com/articles/{obj.slug}/"
```

## Query Optimization

### list_select_related

Use select_related() for ForeignKey lookups in list_display.

```python
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'status']
    list_select_related = ['customer', 'shipping_address']

    @admin.display(description='Customer')
    def customer_name(self, obj):
        return obj.customer.name  # No extra query
```

### get_queryset()

Customize base queryset with optimizations or filters.

```python
class ProductAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Add annotations
        qs = qs.annotate(
            order_count=Count('orders'),
            total_revenue=Sum('orders__total')
        )
        # Add prefetch for reverse relations
        qs = qs.prefetch_related('reviews')
        # Filter by user
        if not request.user.is_superuser:
            qs = qs.filter(owner=request.user)
        return qs
```

### get_search_results()

Customize search behavior and optimization.

```python
class ProductAdmin(admin.ModelAdmin):
    search_fields = ['name', 'sku']

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )

        # Custom search logic
        if search_term.isdigit():
            queryset |= self.model.objects.filter(id=int(search_term))

        # Optimize with select_related
        queryset = queryset.select_related('category')

        return queryset, use_distinct
```

## Filtering and Search

### list_filter

Add filters to sidebar.

```python
class ProductAdmin(admin.ModelAdmin):
    list_filter = [
        'in_stock',           # Boolean field
        'category',           # ForeignKey
        'created_at',         # Date field (auto date ranges)
        'status',             # CharField with choices
        PriceRangeFilter,     # Custom filter
    ]
```

**Built-in date filters:**
- `'created_at'` → Today, Past 7 days, This month, This year
- Can customize with `DateFieldListFilter`

### search_fields

Enable search box.

```python
class ProductAdmin(admin.ModelAdmin):
    search_fields = [
        'name',              # LIKE search
        'sku',
        'description',
        'category__name',    # Search related fields
        '=id',               # Exact match (prefix with =)
        '^name',             # Starts with (prefix with ^)
        '@description',      # Full-text search (PostgreSQL, prefix with @)
    ]
```

**Search prefixes:**
- No prefix: Case-insensitive contains (`icontains`)
- `^`: Starts with (`istartswith`)
- `=`: Exact match (`iexact`)
- `@`: Full-text search (PostgreSQL only)

### search_help_text

Help text above search box.

```python
class ProductAdmin(admin.ModelAdmin):
    search_fields = ['name', 'sku']
    search_help_text = "Search by product name or SKU number"
```

## Actions

### actions

List of bulk actions.

```python
@admin.action(description="Mark as published")
def make_published(modeladmin, request, queryset):
    queryset.update(status='published')

class ArticleAdmin(admin.ModelAdmin):
    actions = [make_published, 'delete_selected']
```

### actions_on_top / actions_on_bottom

Position of action dropdown.

```python
class ProductAdmin(admin.ModelAdmin):
    actions_on_top = True
    actions_on_bottom = False
```

### actions_selection_counter

Show "X of Y selected" counter.

```python
class ProductAdmin(admin.ModelAdmin):
    actions_selection_counter = True  # Default is True
```

## Inlines

### inlines

Related models edited on same page.

```python
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ['product', 'quantity', 'price']

class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
```

**Inline types:**
- `admin.TabularInline`: Compact table format
- `admin.StackedInline`: Stacked fieldsets

**Inline options:**
```python
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1                    # Number of empty forms
    max_num = 10                 # Maximum total forms
    min_num = 1                  # Minimum required forms
    can_delete = True            # Show delete checkbox
    show_change_link = True      # Link to full edit page
    fields = ['product', 'qty']  # Limit fields
    readonly_fields = ['total']  # Readonly fields
    autocomplete_fields = ['product']
    ordering = ['position']      # Override default ordering

    # For many inlines, add:
    classes = ['collapse']       # Start collapsed

    # Customize queryset
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product')
```

## Permissions

### has_add_permission()

Control if user can add objects.

```python
class ArticleAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Only superusers can add
        return request.user.is_superuser
```

### has_change_permission()

Control if user can edit objects (model or object level).

```python
class ArticleAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        if obj is None:
            # Viewing list - check model permission
            return super().has_change_permission(request)
        # Viewing specific object - check ownership
        return obj.author == request.user or request.user.is_superuser
```

### has_delete_permission()

Control if user can delete objects.

```python
class ArticleAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True
        # Only author or superuser can delete
        return obj.author == request.user or request.user.is_superuser
```

### has_view_permission()

Control if user can view objects (Django 2.1+).

```python
class ArticleAdmin(admin.ModelAdmin):
    def has_view_permission(self, request, obj=None):
        # Everyone can view published articles
        if obj and obj.status == 'published':
            return True
        # Only author can view unpublished
        return obj.author == request.user or request.user.is_superuser
```

### has_module_permission()

Control if model appears in admin index.

```python
class ArticleAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        # Only show to editors
        return request.user.groups.filter(name='Editors').exists()
```

### get_readonly_fields()

Dynamic readonly fields based on user or object.

```python
class ArticleAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return []
        if obj and obj.status == 'published':
            return ['title', 'content', 'published_date']
        return ['published_date']
```

## Customization Methods

### get_form()

Customize the ModelForm.

```python
class ArticleAdmin(admin.ModelAdmin):
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Customize form fields
        form.base_fields['author'].initial = request.user
        if not request.user.is_superuser:
            form.base_fields['featured'].widget = forms.HiddenInput()
        return form
```

### get_formsets_with_inlines()

Customize inlines dynamically.

```python
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline, ShippingInline]

    def get_formsets_with_inlines(self, request, obj=None):
        for inline in self.get_inline_instances(request, obj):
            # Skip shipping inline for digital orders
            if isinstance(inline, ShippingInline) and obj and obj.is_digital:
                continue
            yield inline.get_formset(request, obj), inline
```

### get_list_display()

Dynamic list_display.

```python
class ProductAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        default = ['name', 'price', 'category']
        if request.user.is_superuser:
            default.append('internal_cost')
        return default
```

### get_list_filter()

Dynamic filters.

```python
class OrderAdmin(admin.ModelAdmin):
    def get_list_filter(self, request):
        filters = ['status', 'created_at']
        if request.user.is_superuser:
            filters.append('assigned_to')
        return filters
```

### get_urls()

Add custom URLs to admin.

```python
from django.urls import path

class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import/', self.admin_site.admin_view(self.import_view)),
            path('<int:pk>/duplicate/', self.admin_site.admin_view(self.duplicate_view)),
        ]
        return custom_urls + urls

    def import_view(self, request):
        # Custom import page
        pass

    def duplicate_view(self, request, pk):
        # Duplicate object
        pass
```

### save_model()

Hook into save process.

```python
class ArticleAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)
```

### delete_model()

Hook into delete process.

```python
class ArticleAdmin(admin.ModelAdmin):
    def delete_model(self, request, obj):
        # Log deletion
        logger.info(f"User {request.user} deleted {obj}")
        super().delete_model(request, obj)
```

### save_formset()

Hook into inline save process.

```python
class OrderAdmin(admin.ModelAdmin):
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.modified_by = request.user
            instance.save()
        formset.save_m2m()
```

### message_user()

Display messages to user.

```python
from django.contrib import messages

class ProductAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self.message_user(
            request,
            f"Product '{obj.name}' was saved successfully.",
            messages.SUCCESS
        )
```

## Admin Site Options

### admin_site

Use custom AdminSite.

```python
from django.contrib.admin import AdminSite

class MyAdminSite(AdminSite):
    site_header = 'My Admin'
    site_title = 'My Admin Portal'
    index_title = 'Welcome to My Admin'

my_admin_site = MyAdminSite(name='myadmin')
my_admin_site.register(Product, ProductAdmin)

# In urls.py
urlpatterns = [
    path('myadmin/', my_admin_site.urls),
]
```

### Limiting to specific admin sites

```python
class ProductAdmin(admin.ModelAdmin):
    pass

# Register to specific site
admin.site.register(Product, ProductAdmin)
# Or
my_admin_site.register(Product, ProductAdmin)
```

## Complete Example

```python
from django.contrib import admin
from django.db.models import Count, Sum
from django.utils.html import format_html
from .models import Product, ProductImage, Review

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary']
    readonly_fields = ['thumbnail_preview']

    @admin.display(description='Preview')
    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" />', obj.image.url)
        return '-'

@admin.action(description="Mark as featured")
def make_featured(modeladmin, request, queryset):
    updated = queryset.update(featured=True)
    modeladmin.message_user(request, f"{updated} products marked as featured.")

class ProductAdmin(admin.ModelAdmin):
    # Display
    list_display = ['name', 'sku', 'price', 'in_stock', 'review_count', 'revenue']
    list_display_links = ['name', 'sku']
    list_editable = ['price', 'in_stock']
    list_per_page = 50
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    # Search & Filter
    search_fields = ['name', 'sku', 'description', 'category__name']
    list_filter = ['in_stock', 'featured', 'category', 'created_at']

    # Form
    fieldsets = [
        ('Basic Info', {
            'fields': ['name', 'sku', ('price', 'cost')],
        }),
        ('Details', {
            'fields': ['description', 'category', 'tags'],
        }),
        ('Status', {
            'fields': ['in_stock', 'featured'],
        }),
    ]
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['tags']
    autocomplete_fields = ['category']
    prepopulated_fields = {'slug': ['name']}

    # Optimization
    list_select_related = ['category']

    # Actions
    actions = [make_featured]

    # Inlines
    inlines = [ProductImageInline]

    # Save buttons
    save_on_top = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _review_count=Count('reviews'),
            _revenue=Sum('order_items__total')
        ).prefetch_related('images')

    @admin.display(description='Reviews', ordering='_review_count')
    def review_count(self, obj):
        return obj._review_count

    @admin.display(description='Revenue', ordering='_revenue')
    def revenue(self, obj):
        return f"${obj._revenue or 0}"

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj and not request.user.is_superuser:
            return obj.owner == request.user
        return True

admin.site.register(Product, ProductAdmin)
```

## Quick Reference Table

| Option | Purpose | Example Value |
|--------|---------|---------------|
| list_display | Changelist columns | `['name', 'price']` |
| list_filter | Sidebar filters | `['category', 'status']` |
| search_fields | Search box | `['name', 'sku']` |
| list_select_related | Optimize FK queries | `['category', 'author']` |
| ordering | Default sort | `['-created_at']` |
| readonly_fields | Non-editable fields | `['created_at', 'id']` |
| autocomplete_fields | Autocomplete widget | `['product', 'author']` |
| inlines | Related models | `[ItemInline]` |
| actions | Bulk operations | `[make_published]` |
| fieldsets | Form organization | `[('Title', {'fields': [...]})]` |
| date_hierarchy | Date drill-down | `'published_date'` |
| prepopulated_fields | Auto-fill fields | `{'slug': ['title']}` |
| filter_horizontal | M2M widget | `['tags', 'categories']` |
| list_per_page | Pagination size | `25` |
| save_on_top | Duplicate buttons | `True` |

This reference covers all major ModelAdmin options. For complete details, see Django's official documentation.
