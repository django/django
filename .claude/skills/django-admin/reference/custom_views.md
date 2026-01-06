# Custom Admin Views Reference

Complete guide to adding custom views and pages to Django admin.

## Table of Contents

1. [Basic Custom Views](#basic-custom-views)
2. [get_urls() Pattern](#get_urls-pattern)
3. [Admin Context](#admin-context)
4. [Dashboard Widgets](#dashboard-widgets)
5. [Import/Export Views](#importexport-views)
6. [Report Views](#report-views)
7. [Advanced Patterns](#advanced-patterns)

## Basic Custom Views

### Simple Custom View

Add a custom page to the admin.

```python
from django.contrib import admin
from django.shortcuts import render
from django.urls import path

class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('stats/', self.admin_site.admin_view(self.stats_view)),
        ]
        return custom_urls + urls

    def stats_view(self, request):
        context = dict(
            # Include common admin context
            self.admin_site.each_context(request),
            # Custom context
            title='Product Statistics',
            total_products=Product.objects.count(),
        )
        return render(request, 'admin/products/stats.html', context)

admin.site.register(Product, ProductAdmin)
```

**Template (admin/products/stats.html):**

```html
{% extends "admin/base_site.html" %}

{% block content %}
<h1>{{ title }}</h1>

<div class="module">
  <p>Total Products: {{ total_products }}</p>
</div>
{% endblock %}
```

### Custom View with Form

```python
from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path

class ImportForm(forms.Form):
    file = forms.FileField(label='CSV File')

class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import/', self.admin_site.admin_view(self.import_view)),
        ]
        return custom_urls + urls

    def import_view(self, request):
        if request.method == 'POST':
            form = ImportForm(request.POST, request.FILES)
            if form.is_valid():
                # Process file
                file = form.cleaned_data['file']
                # ... import logic ...
                messages.success(request, 'Import successful')
                return redirect('..')
        else:
            form = ImportForm()

        context = dict(
            self.admin_site.each_context(request),
            title='Import Products',
            form=form,
        )
        return render(request, 'admin/products/import.html', context)
```

## get_urls() Pattern

### URL Structure

Custom URLs are added before default admin URLs.

```python
class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        # Get default admin URLs
        urls = super().get_urls()

        # Define custom URLs
        custom_urls = [
            path('import/', self.admin_site.admin_view(self.import_view), name='import'),
            path('export/', self.admin_site.admin_view(self.export_view), name='export'),
            path('<int:product_id>/clone/', self.admin_site.admin_view(self.clone_view), name='clone'),
        ]

        # Custom URLs come first (so they match before defaults)
        return custom_urls + urls

    def import_view(self, request):
        # URL: /admin/products/product/import/
        pass

    def export_view(self, request):
        # URL: /admin/products/product/export/
        pass

    def clone_view(self, request, product_id):
        # URL: /admin/products/product/123/clone/
        pass
```

### admin_site.admin_view()

Wraps view with admin authentication and permissions.

```python
class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # Wrapped view - requires login and staff status
            path('stats/', self.admin_site.admin_view(self.stats_view)),

            # Without wrapper - no auth required (not recommended)
            # path('public/', self.public_view),
        ]
        return custom_urls + urls

    def stats_view(self, request):
        # User is authenticated and is_staff=True
        # Automatically redirected to login if not authenticated
        pass
```

### Permission-Protected Views

Require specific permissions for custom views.

```python
from django.core.exceptions import PermissionDenied

class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import/', self.admin_site.admin_view(self.import_view)),
        ]
        return custom_urls + urls

    def import_view(self, request):
        # Check permission
        if not self.has_import_permission(request):
            raise PermissionDenied

        # View logic...
        pass

    def has_import_permission(self, request):
        """Check if user can import"""
        return (
            request.user.has_perm('products.add_product') and
            request.user.groups.filter(name='Importers').exists()
        )
```

### Object-Specific Custom Views

Views that operate on specific objects.

```python
class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:product_id>/clone/',
                self.admin_site.admin_view(self.clone_view),
                name='product_clone'
            ),
        ]
        return custom_urls + urls

    def clone_view(self, request, product_id):
        # Get object
        product = self.get_object(request, product_id)

        if product is None:
            self.message_user(
                request,
                'Product not found',
                level=messages.ERROR
            )
            return redirect('..')

        # Check permissions
        if not self.has_change_permission(request, product):
            raise PermissionDenied

        # Clone product
        product.pk = None
        product.name = f"{product.name} (Copy)"
        product.save()

        self.message_user(
            request,
            f'Cloned product: {product.name}'
        )
        return redirect('admin:products_product_change', product.id)
```

## Admin Context

### Standard Admin Context

Always include admin context for consistent UI.

```python
def stats_view(self, request):
    context = dict(
        # Includes: site_header, site_title, available_apps, etc.
        self.admin_site.each_context(request),

        # Your custom context
        title='Statistics',
        products=Product.objects.all(),
    )
    return render(request, 'admin/stats.html', context)
```

### Admin Context Variables

Available context variables from `each_context()`:

```python
{
    'site_title': 'Django admin',
    'site_header': 'Django administration',
    'site_url': '/',
    'has_permission': True/False,
    'available_apps': [...],  # Admin apps user can access
    'is_popup': False,
    'is_nav_sidebar_enabled': True,
}
```

### Custom Context for All Views

Add context to all admin views.

```python
from django.contrib import admin

class MyAdminSite(admin.AdminSite):
    def each_context(self, request):
        context = super().each_context(request)
        context.update({
            'custom_var': 'custom value',
            'user_role': request.user.groups.first(),
        })
        return context

my_admin = MyAdminSite(name='myadmin')
```

## Dashboard Widgets

### Custom Admin Index

Add custom content to admin index page.

```python
# admin.py
from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path

class MyAdminSite(admin.AdminSite):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_view(self.custom_index), name='index'),
        ]
        # Override default index
        return custom_urls[:-1] + urls[1:]

    def custom_index(self, request, extra_context=None):
        # Add custom dashboard data
        context = {
            **self.each_context(request),
            'title': 'Dashboard',
            'total_users': User.objects.count(),
            'total_products': Product.objects.count(),
            'recent_orders': Order.objects.order_by('-created_at')[:5],
        }
        if extra_context:
            context.update(extra_context)

        return TemplateResponse(
            request,
            'admin/custom_index.html',
            context
        )

my_admin = MyAdminSite(name='myadmin')
my_admin.register(Product, ProductAdmin)

# urls.py
urlpatterns = [
    path('admin/', my_admin.urls),
]
```

**Template (admin/custom_index.html):**

```html
{% extends "admin/index.html" %}
{% load i18n static %}

{% block content %}
{{ block.super }}

<div class="module">
  <h2>Quick Stats</h2>
  <table>
    <tr>
      <th>Total Users:</th>
      <td>{{ total_users }}</td>
    </tr>
    <tr>
      <th>Total Products:</th>
      <td>{{ total_products }}</td>
    </tr>
  </table>
</div>

<div class="module">
  <h2>Recent Orders</h2>
  <ul>
    {% for order in recent_orders %}
    <li>
      <a href="{% url 'admin:orders_order_change' order.id %}">
        Order #{{ order.id }} - {{ order.customer }}
      </a>
    </li>
    {% endfor %}
  </ul>
</div>
{% endblock %}
```

### App-Specific Dashboard

Add dashboard to specific app.

```python
class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view)),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        from django.db.models import Sum, Count, Avg

        context = dict(
            self.admin_site.each_context(request),
            title='Product Dashboard',
            total_products=Product.objects.count(),
            total_value=Product.objects.aggregate(
                total=Sum('price')
            )['total'],
            avg_price=Product.objects.aggregate(
                avg=Avg('price')
            )['avg'],
            by_category=Product.objects.values('category__name').annotate(
                count=Count('id'),
                total_value=Sum('price')
            ).order_by('-count'),
        )
        return render(request, 'admin/products/dashboard.html', context)
```

## Import/Export Views

### CSV Import

```python
import csv
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django import forms

class ImportCSVForm(forms.Form):
    csv_file = forms.FileField(label='CSV File')

class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv)),
        ]
        return custom_urls + urls

    def import_csv(self, request):
        if request.method == 'POST':
            form = ImportCSVForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES['csv_file']

                # Decode file
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(decoded_file)

                created = 0
                updated = 0
                errors = []

                for row_num, row in enumerate(reader, start=2):
                    try:
                        product, created_flag = Product.objects.update_or_create(
                            sku=row['sku'],
                            defaults={
                                'name': row['name'],
                                'price': row['price'],
                            }
                        )
                        if created_flag:
                            created += 1
                        else:
                            updated += 1
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")

                # Report results
                if created:
                    messages.success(request, f"Created {created} products")
                if updated:
                    messages.info(request, f"Updated {updated} products")
                if errors:
                    for error in errors[:5]:  # Show first 5 errors
                        messages.error(request, error)
                    if len(errors) > 5:
                        messages.error(request, f"... and {len(errors) - 5} more errors")

                return redirect('..')
        else:
            form = ImportCSVForm()

        context = dict(
            self.admin_site.each_context(request),
            title='Import Products from CSV',
            form=form,
        )
        return render(request, 'admin/products/import_csv.html', context)
```

### CSV Export

```python
import csv
from django.http import HttpResponse

class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export-csv/', self.admin_site.admin_view(self.export_csv)),
        ]
        return custom_urls + urls

    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="products.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'SKU', 'Price', 'In Stock'])

        # Apply current filters if present
        queryset = self.get_queryset(request)
        # Apply search if present
        search_term = request.GET.get('q', '')
        if search_term:
            queryset, _ = self.get_search_results(request, queryset, search_term)

        # Write data
        for product in queryset:
            writer.writerow([
                product.id,
                product.name,
                product.sku,
                product.price,
                product.in_stock,
            ])

        return response
```

### Excel Export

```python
from openpyxl import Workbook
from django.http import HttpResponse

class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export-excel/', self.admin_site.admin_view(self.export_excel)),
        ]
        return custom_urls + urls

    def export_excel(self, request):
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="products.xlsx"'

        wb = Workbook()
        ws = wb.active
        ws.title = "Products"

        # Headers
        headers = ['ID', 'Name', 'SKU', 'Price', 'In Stock']
        ws.append(headers)

        # Data
        for product in Product.objects.all():
            ws.append([
                product.id,
                product.name,
                product.sku,
                float(product.price),
                product.in_stock,
            ])

        wb.save(response)
        return response
```

## Report Views

### Analytics Report

```python
from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncDate

class OrderAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('reports/', self.admin_site.admin_view(self.reports_view)),
        ]
        return custom_urls + urls

    def reports_view(self, request):
        from datetime import timedelta
        from django.utils import timezone

        # Date range from request or default to last 30 days
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        # Daily order stats
        daily_stats = Order.objects.filter(
            created_at__gte=start_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            order_count=Count('id'),
            total_revenue=Sum('total'),
            avg_order=Avg('total')
        ).order_by('date')

        # Top customers
        top_customers = Order.objects.filter(
            created_at__gte=start_date
        ).values('customer__name').annotate(
            order_count=Count('id'),
            total_spent=Sum('total')
        ).order_by('-total_spent')[:10]

        # Product sales
        top_products = OrderItem.objects.filter(
            order__created_at__gte=start_date
        ).values('product__name').annotate(
            quantity_sold=Sum('quantity'),
            revenue=Sum('total')
        ).order_by('-revenue')[:10]

        context = dict(
            self.admin_site.each_context(request),
            title='Sales Reports',
            start_date=start_date,
            end_date=end_date,
            daily_stats=daily_stats,
            top_customers=top_customers,
            top_products=top_products,
        )
        return render(request, 'admin/orders/reports.html', context)
```

**Template (admin/orders/reports.html):**

```html
{% extends "admin/base_site.html" %}

{% block content %}
<h1>{{ title }}</h1>
<p>{{ start_date|date:"Y-m-d" }} to {{ end_date|date:"Y-m-d" }}</p>

<div class="module">
  <h2>Daily Statistics</h2>
  <table>
    <thead>
      <tr>
        <th>Date</th>
        <th>Orders</th>
        <th>Revenue</th>
        <th>Avg Order</th>
      </tr>
    </thead>
    <tbody>
      {% for stat in daily_stats %}
      <tr>
        <td>{{ stat.date }}</td>
        <td>{{ stat.order_count }}</td>
        <td>${{ stat.total_revenue|floatformat:2 }}</td>
        <td>${{ stat.avg_order|floatformat:2 }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<div class="module">
  <h2>Top Customers</h2>
  <table>
    <thead>
      <tr>
        <th>Customer</th>
        <th>Orders</th>
        <th>Total Spent</th>
      </tr>
    </thead>
    <tbody>
      {% for customer in top_customers %}
      <tr>
        <td>{{ customer.customer__name }}</td>
        <td>{{ customer.order_count }}</td>
        <td>${{ customer.total_spent|floatformat:2 }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<div class="module">
  <h2>Top Products</h2>
  <table>
    <thead>
      <tr>
        <th>Product</th>
        <th>Quantity Sold</th>
        <th>Revenue</th>
      </tr>
    </thead>
    <tbody>
      {% for product in top_products %}
      <tr>
        <td>{{ product.product__name }}</td>
        <td>{{ product.quantity_sold }}</td>
        <td>${{ product.revenue|floatformat:2 }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
```

### Chart/Visualization View

```python
import json
from django.db.models import Count
from django.db.models.functions import TruncMonth

class OrderAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('charts/', self.admin_site.admin_view(self.charts_view)),
        ]
        return custom_urls + urls

    def charts_view(self, request):
        # Monthly order data for chart
        monthly_data = Order.objects.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        # Format for JavaScript chart library
        chart_labels = [item['month'].strftime('%Y-%m') for item in monthly_data]
        chart_data = [item['count'] for item in monthly_data]

        context = dict(
            self.admin_site.each_context(request),
            title='Order Charts',
            chart_labels=json.dumps(chart_labels),
            chart_data=json.dumps(chart_data),
        )
        return render(request, 'admin/orders/charts.html', context)
```

**Template with Chart.js:**

```html
{% extends "admin/base_site.html" %}

{% block extrahead %}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
{% endblock %}

{% block content %}
<h1>{{ title }}</h1>

<div class="module">
  <canvas id="ordersChart"></canvas>
</div>

<script>
const ctx = document.getElementById('ordersChart');
new Chart(ctx, {
  type: 'line',
  data: {
    labels: {{ chart_labels|safe }},
    datasets: [{
      label: 'Orders per Month',
      data: {{ chart_data|safe }},
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1
    }]
  }
});
</script>
{% endblock %}
```

## Advanced Patterns

### Multi-Step Wizard

```python
class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-wizard/', self.admin_site.admin_view(self.import_wizard)),
            path('import-wizard/step2/', self.admin_site.admin_view(self.import_wizard_step2)),
            path('import-wizard/step3/', self.admin_site.admin_view(self.import_wizard_step3)),
        ]
        return custom_urls + urls

    def import_wizard(self, request):
        """Step 1: Upload file"""
        if request.method == 'POST':
            # Store file in session
            request.session['import_file'] = request.FILES['file'].read().decode('utf-8')
            return redirect('admin:products_product_import_wizard_step2')

        context = dict(
            self.admin_site.each_context(request),
            title='Import Wizard - Step 1',
        )
        return render(request, 'admin/products/import_step1.html', context)

    def import_wizard_step2(self, request):
        """Step 2: Map columns"""
        # Get file from session
        file_data = request.session.get('import_file')
        # Parse and show mapping form
        # ...
        pass

    def import_wizard_step3(self, request):
        """Step 3: Confirm and import"""
        # Execute import
        # ...
        pass
```

### AJAX Endpoint

```python
from django.http import JsonResponse

class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('ajax/search/', self.admin_site.admin_view(self.ajax_search)),
        ]
        return custom_urls + urls

    def ajax_search(self, request):
        query = request.GET.get('q', '')
        products = Product.objects.filter(
            name__icontains=query
        )[:10]

        results = [
            {'id': p.id, 'name': p.name, 'price': str(p.price)}
            for p in products
        ]

        return JsonResponse({'results': results})
```

### Bulk Operation View

```python
class ProductAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-update/', self.admin_site.admin_view(self.bulk_update_view)),
        ]
        return custom_urls + urls

    def bulk_update_view(self, request):
        if request.method == 'POST':
            # Get selected IDs
            selected_ids = request.POST.getlist('ids')
            update_data = {
                'field': request.POST.get('field'),
                'value': request.POST.get('value'),
            }

            # Update
            Product.objects.filter(id__in=selected_ids).update(
                **{update_data['field']: update_data['value']}
            )

            messages.success(request, f"Updated {len(selected_ids)} products")
            return redirect('..')

        # Show form
        context = dict(
            self.admin_site.each_context(request),
            title='Bulk Update',
        )
        return render(request, 'admin/products/bulk_update.html', context)
```

## Best Practices

1. **Use admin_site.admin_view()**: Always wrap views for authentication
2. **Include Admin Context**: Use `each_context()` for consistent UI
3. **Check Permissions**: Verify user permissions before processing
4. **Provide Feedback**: Use `message_user()` for user notifications
5. **Handle Errors**: Catch exceptions and show helpful messages
6. **Use Transactions**: Wrap bulk operations in transactions
7. **Test Edge Cases**: Empty querysets, invalid input, etc.

## Complete Example

```python
from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import messages
from django.http import HttpResponse
import csv

class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'price', 'in_stock']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard)),
            path('import/', self.admin_site.admin_view(self.import_csv)),
            path('export/', self.admin_site.admin_view(self.export_csv)),
        ]
        return custom_urls + urls

    def dashboard(self, request):
        from django.db.models import Count, Sum

        context = dict(
            self.admin_site.each_context(request),
            title='Product Dashboard',
            total_products=Product.objects.count(),
            total_value=Product.objects.aggregate(Sum('price'))['price__sum'],
            by_category=Product.objects.values('category__name').annotate(
                count=Count('id')
            ),
        )
        return render(request, 'admin/products/dashboard.html', context)

    def import_csv(self, request):
        if request.method == 'POST':
            csv_file = request.FILES['csv_file']
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            created = 0
            for row in reader:
                Product.objects.get_or_create(
                    sku=row['sku'],
                    defaults={'name': row['name'], 'price': row['price']}
                )
                created += 1

            messages.success(request, f"Imported {created} products")
            return redirect('..')

        context = dict(
            self.admin_site.each_context(request),
            title='Import Products',
        )
        return render(request, 'admin/products/import.html', context)

    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="products.csv"'

        writer = csv.writer(response)
        writer.writerow(['Name', 'SKU', 'Price'])

        for product in Product.objects.all():
            writer.writerow([product.name, product.sku, product.price])

        return response

admin.site.register(Product, ProductAdmin)
```
