# Django Class-Based View Mixins Reference

## Table of Contents

- [Inheritance Hierarchy](#inheritance-hierarchy)
- [Generic View Classes](#generic-view-classes)
- [Mixin Catalog](#mixin-catalog)
- [Mixin Composition Patterns](#mixin-composition-patterns)
- [Method Resolution Order (MRO)](#method-resolution-order-mro)
- [Custom Mixin Examples](#custom-mixin-examples)

## Inheritance Hierarchy

```
View (base class)
│
├─ TemplateResponseMixin + TemplateView
│
├─ RedirectView
│
├─ SingleObjectMixin + SingleObjectTemplateResponseMixin
│  └─ DetailView
│  └─ FormMixin + ProcessFormView + ModelFormMixin
│     └─ CreateView
│     └─ UpdateView
│
├─ MultipleObjectMixin + MultipleObjectTemplateResponseMixin
│  └─ ListView
│
└─ FormMixin + ProcessFormView
   └─ FormView
   └─ DeletionMixin + DeleteView
```

## Generic View Classes

### Base Views

#### View
**Purpose:** Base class for all views
**Key Methods:**
- `as_view()` - Class method to create view function
- `dispatch(request, *args, **kwargs)` - Route to HTTP method handlers
- `http_method_not_allowed()` - Handle unsupported methods

**Usage:**
```python
from django.views import View
from django.http import HttpResponse

class MyView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse('GET response')

    def post(self, request, *args, **kwargs):
        return HttpResponse('POST response')
```

#### TemplateView
**Purpose:** Render a template
**Inherits:** `TemplateResponseMixin`, `ContextMixin`, `View`
**Key Attributes:**
- `template_name` - Template path
- `content_type` - Response content type
- `extra_context` - Static context dict

**Usage:**
```python
from django.views.generic import TemplateView

class AboutView(TemplateView):
    template_name = 'about.html'
    extra_context = {'company': 'Acme Corp'}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['year'] = datetime.now().year
        return context
```

#### RedirectView
**Purpose:** Redirect to another URL
**Key Attributes:**
- `url` - Static URL to redirect to
- `pattern_name` - URL pattern name
- `permanent` - 301 vs 302 redirect
- `query_string` - Preserve query string

**Usage:**
```python
from django.views.generic import RedirectView

class OldArticleView(RedirectView):
    pattern_name = 'article-detail'
    permanent = True

    def get_redirect_url(self, *args, **kwargs):
        # Redirect old IDs to new ones
        old_id = kwargs['old_id']
        new_id = migrate_id(old_id)
        return super().get_redirect_url(pk=new_id)
```

### Display Views

#### ListView
**Purpose:** Display list of objects
**Inherits:** `MultipleObjectTemplateResponseMixin`, `BaseListView`
**Key Attributes:**
- `model` - Model class
- `queryset` - Custom queryset
- `context_object_name` - Context variable name
- `paginate_by` - Items per page
- `ordering` - Default ordering

**Key Methods:**
- `get_queryset()` - Return queryset
- `get_context_data()` - Add extra context
- `get_paginate_by()` - Dynamic pagination size

**Usage:**
```python
from django.views.generic import ListView

class ArticleListView(ListView):
    model = Article
    template_name = 'blog/article_list.html'
    context_object_name = 'articles'
    paginate_by = 20
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(published=True).select_related('author')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context
```

#### DetailView
**Purpose:** Display single object
**Inherits:** `SingleObjectTemplateResponseMixin`, `BaseDetailView`
**Key Attributes:**
- `model` - Model class
- `slug_field` - Field name for slug
- `slug_url_kwarg` - URL kwarg name
- `pk_url_kwarg` - URL kwarg for pk

**Usage:**
```python
from django.views.generic import DetailView

class ArticleDetailView(DetailView):
    model = Article
    template_name = 'blog/article_detail.html'
    context_object_name = 'article'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return super().get_queryset().select_related(
            'author'
        ).prefetch_related('tags', 'comments__author')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_articles'] = Article.objects.filter(
            tags__in=self.object.tags.all()
        ).exclude(pk=self.object.pk).distinct()[:5]
        return context
```

### Editing Views

#### FormView
**Purpose:** Display and process form
**Inherits:** `TemplateResponseMixin`, `BaseFormView`
**Key Attributes:**
- `form_class` - Form class
- `success_url` - Redirect after success
- `initial` - Initial form data

**Key Methods:**
- `get_form_class()` - Return form class
- `get_initial()` - Return initial data
- `form_valid(form)` - Handle valid form
- `form_invalid(form)` - Handle invalid form

**Usage:**
```python
from django.views.generic import FormView

class ContactView(FormView):
    template_name = 'contact.html'
    form_class = ContactForm
    success_url = '/thanks/'

    def form_valid(self, form):
        # Send email
        form.send_email()
        return super().form_valid(form)

    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.is_authenticated:
            initial['email'] = self.request.user.email
        return initial
```

#### CreateView
**Purpose:** Create new model instance
**Inherits:** `SingleObjectTemplateResponseMixin`, `BaseCreateView`
**Key Attributes:**
- `model` - Model class
- `form_class` - ModelForm class
- `fields` - Fields to include (if no form_class)
- `success_url` - Redirect URL

**Usage:**
```python
from django.views.generic import CreateView
from django.urls import reverse_lazy

class ArticleCreateView(CreateView):
    model = Article
    form_class = ArticleForm
    template_name = 'blog/article_form.html'
    success_url = reverse_lazy('article-list')

    def form_valid(self, form):
        # Set author before saving
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        return context
```

#### UpdateView
**Purpose:** Update existing model instance
**Inherits:** `SingleObjectTemplateResponseMixin`, `BaseUpdateView`
**Similar to CreateView but operates on existing object**

**Usage:**
```python
from django.views.generic import UpdateView

class ArticleUpdateView(UpdateView):
    model = Article
    form_class = ArticleForm
    template_name = 'blog/article_form.html'

    def get_queryset(self):
        # Only allow editing own articles
        return Article.objects.filter(author=self.request.user)

    def get_success_url(self):
        return reverse('article-detail', kwargs={'pk': self.object.pk})
```

#### DeleteView
**Purpose:** Delete model instance with confirmation
**Inherits:** `SingleObjectTemplateResponseMixin`, `BaseDeleteView`
**Key Attributes:**
- `success_url` - Where to redirect after deletion

**Usage:**
```python
from django.views.generic import DeleteView
from django.urls import reverse_lazy

class ArticleDeleteView(DeleteView):
    model = Article
    template_name = 'blog/article_confirm_delete.html'
    success_url = reverse_lazy('article-list')

    def get_queryset(self):
        # Only allow deleting own articles
        return Article.objects.filter(author=self.request.user)

    def delete(self, request, *args, **kwargs):
        # Custom logic before deletion
        messages.success(request, 'Article deleted successfully')
        return super().delete(request, *args, **kwargs)
```

## Mixin Catalog

### Access Mixins (django.contrib.auth.mixins)

#### LoginRequiredMixin
**Purpose:** Require user to be authenticated
**Attributes:**
- `login_url` - Login page URL
- `redirect_field_name` - Query param name

```python
from django.contrib.auth.mixins import LoginRequiredMixin

class ProfileView(LoginRequiredMixin, DetailView):
    model = Profile
    login_url = '/login/'
    redirect_field_name = 'next'
```

#### PermissionRequiredMixin
**Purpose:** Require specific permissions
**Attributes:**
- `permission_required` - Permission string or list
- `raise_exception` - Raise 403 instead of redirect

```python
from django.contrib.auth.mixins import PermissionRequiredMixin

class ArticleDeleteView(PermissionRequiredMixin, DeleteView):
    model = Article
    permission_required = 'blog.delete_article'
    raise_exception = True

    def has_permission(self):
        # Custom permission check
        obj = self.get_object()
        return obj.author == self.request.user
```

#### UserPassesTestMixin
**Purpose:** Custom permission logic
**Methods:**
- `test_func()` - Return True if access allowed

```python
from django.contrib.auth.mixins import UserPassesTestMixin

class ArticleUpdateView(UserPassesTestMixin, UpdateView):
    model = Article

    def test_func(self):
        article = self.get_object()
        return article.author == self.request.user or self.request.user.is_staff
```

### Content Mixins

#### ContextMixin
**Purpose:** Add context data to templates
**Methods:**
- `get_context_data(**kwargs)` - Return context dict

```python
from django.views.generic.base import ContextMixin

class BreadcrumbMixin(ContextMixin):
    breadcrumb = []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumb'] = self.breadcrumb
        return context

class ArticleDetailView(BreadcrumbMixin, DetailView):
    breadcrumb = [
        {'title': 'Home', 'url': '/'},
        {'title': 'Articles', 'url': '/articles/'},
    ]
```

#### SingleObjectMixin
**Purpose:** Work with single model object
**Key Methods:**
- `get_object()` - Retrieve object
- `get_queryset()` - Return queryset
- `get_slug_field()` - Return slug field name

#### MultipleObjectMixin
**Purpose:** Work with list of objects
**Key Methods:**
- `get_queryset()` - Return queryset
- `get_ordering()` - Return ordering
- `paginate_queryset()` - Apply pagination

### Template Mixins

#### TemplateResponseMixin
**Purpose:** Render template to HttpResponse
**Attributes:**
- `template_name` - Template path
- `template_engine` - Template engine name
- `response_class` - Response class to use
- `content_type` - Response content type

**Methods:**
- `render_to_response(context)` - Render template
- `get_template_names()` - Return list of templates

### Form Mixins

#### FormMixin
**Purpose:** Handle form display and processing
**Key Methods:**
- `get_form()` - Instantiate form
- `get_form_class()` - Return form class
- `get_initial()` - Initial form data
- `form_valid(form)` - Success handler
- `form_invalid(form)` - Error handler

#### ModelFormMixin
**Purpose:** Handle ModelForm instances
**Combines:** `FormMixin`, `SingleObjectMixin`
**Additional Methods:**
- `get_form_kwargs()` - Include instance

## Mixin Composition Patterns

### Pattern 1: Access Control + CRUD

```python
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import UpdateView

class ArticleUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Order matters: Access checks before view logic."""
    model = Article
    fields = ['title', 'content']

    def test_func(self):
        return self.get_object().author == self.request.user
```

### Pattern 2: Multiple Custom Mixins

```python
class AjaxResponseMixin:
    """Return JSON for AJAX requests."""
    def render_to_json_response(self, context):
        return JsonResponse(context)

    def form_valid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.render_to_json_response({'success': True})
        return super().form_valid(form)

class TimestampMixin:
    """Add created/modified by user."""
    def form_valid(self, form):
        if not form.instance.pk:
            form.instance.created_by = self.request.user
        form.instance.modified_by = self.request.user
        return super().form_valid(form)

class ArticleCreateView(
    LoginRequiredMixin,
    AjaxResponseMixin,
    TimestampMixin,
    CreateView
):
    model = Article
    fields = ['title', 'content']
```

### Pattern 3: Generic List Filtering

```python
class FilterMixin:
    """Add filtering from query params."""
    filter_fields = []

    def get_queryset(self):
        qs = super().get_queryset()
        filters = {}
        for field in self.filter_fields:
            value = self.request.GET.get(field)
            if value:
                filters[field] = value
        return qs.filter(**filters)

class ArticleListView(FilterMixin, ListView):
    model = Article
    filter_fields = ['category', 'author', 'published']
```

### Pattern 4: Multi-Step Form Processing

```python
class StepMixin:
    """Handle multi-step forms."""
    step = 1
    steps = 3

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['step'] = self.step
        context['total_steps'] = self.steps
        return context

    def form_valid(self, form):
        # Store in session
        step_data = self.request.session.get('form_data', {})
        step_data[f'step_{self.step}'] = form.cleaned_data
        self.request.session['form_data'] = step_data

        if self.step < self.steps:
            return redirect('form-step', step=self.step + 1)
        else:
            # Final step: process all data
            return self.process_all_steps(step_data)

class RegistrationStep1(StepMixin, FormView):
    step = 1
    form_class = PersonalInfoForm
```

## Method Resolution Order (MRO)

**Understanding MRO is critical for debugging mixin issues.**

### Example MRO

```python
class MyView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    pass

# MRO:
# MyView → LoginRequiredMixin → PermissionRequiredMixin → UpdateView
# → SingleObjectTemplateResponseMixin → TemplateResponseMixin
# → BaseUpdateView → ModelFormMixin → FormMixin
# → SingleObjectMixin → ContextMixin → ProcessFormView
# → View → object
```

**Check MRO:**
```python
print(MyView.__mro__)
# or
import inspect
print(inspect.getmro(MyView))
```

### MRO Rules

1. **Left-to-right:** Mixins are checked left to right
2. **super() calls all:** Each mixin should call `super()` to continue chain
3. **Access first:** Put access mixins (LoginRequired, etc.) leftmost
4. **Base last:** Generic view (ListView, etc.) goes rightmost

### Common MRO Issues

**Problem: Mixin method not called**
```python
# BAD - FormMixin doesn't call super()
class BadMixin:
    def form_valid(self, form):
        print("My logic")
        # Missing super() call!
        return redirect('success')

# GOOD - Always call super()
class GoodMixin:
    def form_valid(self, form):
        print("My logic")
        return super().form_valid(form)
```

**Problem: Wrong mixin order**
```python
# BAD - LoginRequired after view logic
class BadView(UpdateView, LoginRequiredMixin):
    pass  # dispatch() called before login check!

# GOOD - Access checks first
class GoodView(LoginRequiredMixin, UpdateView):
    pass
```

## Custom Mixin Examples

### JSONResponseMixin

```python
from django.http import JsonResponse

class JSONResponseMixin:
    """Render response as JSON."""
    def render_to_json_response(self, context, **kwargs):
        return JsonResponse(self.get_data(context), **kwargs)

    def get_data(self, context):
        """Override to customize JSON output."""
        return context

class ArticleListAPIView(JSONResponseMixin, ListView):
    model = Article

    def render_to_response(self, context, **kwargs):
        return self.render_to_json_response(context, **kwargs)

    def get_data(self, context):
        return {
            'articles': [
                {'id': a.id, 'title': a.title}
                for a in context['object_list']
            ]
        }
```

### CacheMixin

```python
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

class CacheMixin:
    """Add caching to view."""
    cache_timeout = 60 * 15  # 15 minutes

    @method_decorator(cache_page(cache_timeout))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

class ArticleListView(CacheMixin, ListView):
    model = Article
    cache_timeout = 60 * 30  # Override: 30 minutes
```

### PrefetchMixin

```python
class PrefetchMixin:
    """Automatically optimize queries."""
    prefetch_related_fields = []
    select_related_fields = []

    def get_queryset(self):
        qs = super().get_queryset()
        if self.select_related_fields:
            qs = qs.select_related(*self.select_related_fields)
        if self.prefetch_related_fields:
            qs = qs.prefetch_related(*self.prefetch_related_fields)
        return qs

class ArticleDetailView(PrefetchMixin, DetailView):
    model = Article
    select_related_fields = ['author', 'category']
    prefetch_related_fields = ['tags', 'comments__author']
```

### ExportMixin

```python
import csv
from django.http import HttpResponse

class ExportMixin:
    """Export queryset to CSV."""
    export_fields = []
    export_filename = 'export.csv'

    def export_csv(self):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.export_filename}"'

        writer = csv.writer(response)
        writer.writerow(self.export_fields)

        for obj in self.get_queryset():
            writer.writerow([
                getattr(obj, field) for field in self.export_fields
            ])

        return response

    def get(self, request, *args, **kwargs):
        if request.GET.get('export') == 'csv':
            return self.export_csv()
        return super().get(request, *args, **kwargs)

class ArticleListView(ExportMixin, ListView):
    model = Article
    export_fields = ['id', 'title', 'author', 'created_at']
    export_filename = 'articles.csv'
```

## Best Practices

1. **Always call super()** in overridden methods
2. **Put access mixins first** in inheritance list
3. **Generic view goes last** in inheritance list
4. **Keep mixins focused** - single responsibility
5. **Document mixin requirements** - what it expects from other classes
6. **Use composition** over deep inheritance when possible
7. **Test MRO** when debugging weird behavior
8. **Avoid state in mixins** - rely on view attributes
