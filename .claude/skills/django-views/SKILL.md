# Django Views & URL Routing Skill

## Overview

This skill helps you build Django views (function-based and class-based), configure URL routing, handle HTTP operations, and implement common patterns like REST APIs, file handling, pagination, caching, and async views.

**Use this skill when you need to:**
- Create new views or refactor existing ones
- Build REST APIs without Django REST Framework
- Handle file uploads/downloads
- Implement pagination
- Add view-level caching
- Choose between FBV and CBV
- Configure URL patterns and routing
- Build async views

## Quick Start

**Most common workflow (Create a CRUD view):**

1. Generate the view skeleton:
   ```bash
   python .claude/skills/django-views/scripts/generate_view.py \
     --name ArticleListView --type list --model Article --app blog
   ```

2. Add URL pattern to your app's `urls.py`:
   ```python
   from django.urls import path
   from .views import ArticleListView

   urlpatterns = [
       path('articles/', ArticleListView.as_view(), name='article-list'),
   ]
   ```

3. Test the view:
   ```python
   from django.test import TestCase

   class ArticleListViewTest(TestCase):
       def test_list_view(self):
           response = self.client.get('/articles/')
           self.assertEqual(response.status_code, 200)
   ```

## When to Use This Skill

- [ ] Need to handle HTTP requests/responses
- [ ] Building CRUD operations
- [ ] Creating REST API endpoints
- [ ] Implementing file upload/download
- [ ] Adding pagination to listings
- [ ] Caching view responses
- [ ] Building async views

## Core Workflows

### Workflow 1: Create a Class-Based View

**When:** CRUD operations, code reuse via mixins, OOP patterns.

**Steps:**

1. **Choose base class:**
   - `ListView` - List objects
   - `DetailView` - Single object
   - `CreateView` - Create object
   - `UpdateView` - Edit object
   - `DeleteView` - Delete object
   - `FormView` - Form submission
   - `TemplateView` - Template only

2. **Create view:**
   ```python
   from django.views.generic import ListView
   from .models import Article

   class ArticleListView(ListView):
       model = Article
       template_name = 'blog/article_list.html'
       paginate_by = 20

       def get_queryset(self):
           return Article.objects.select_related('author').filter(
               published=True
           ).order_by('-created_at')
   ```

3. **Configure URL:**
   ```python
   path('articles/', ArticleListView.as_view(), name='article-list'),
   ```

**See:** `reference/cbv_mixins.md` for comprehensive mixin patterns

### Workflow 2: Build REST API Without DRF

**When:** Simple JSON API without DRF overhead.

**Steps:**

1. **Create API view:**
   ```python
   from django.http import JsonResponse
   from django.views.decorators.http import require_http_methods
   import json

   @require_http_methods(["GET"])
   def article_list_api(request):
       articles = Article.objects.filter(published=True).select_related('author')

       return JsonResponse({
           'count': articles.count(),
           'results': [
               {'id': a.id, 'title': a.title, 'author': a.author.username}
               for a in articles
           ]
       })

   @require_http_methods(["POST"])
   def article_create_api(request):
       data = json.loads(request.body)

       article = Article.objects.create(
           title=data['title'],
           content=data['content'],
           author=request.user
       )

       return JsonResponse({'id': article.id}, status=201)
   ```

2. **Add error handling:**
   ```python
   from functools import wraps

   def api_exception_handler(view_func):
       @wraps(view_func)
       def wrapper(request, *args, **kwargs):
           try:
               return view_func(request, *args, **kwargs)
           except Article.DoesNotExist:
               return JsonResponse({'error': 'Not found'}, status=404)
           except Exception as e:
               return JsonResponse({'error': str(e)}, status=500)
       return wrapper
   ```

**See:** `reference/api_patterns.md` for complete API patterns

### Workflow 3: Handle File Downloads/Uploads

**Download:**
```python
from django.http import FileResponse
from django.views.decorators.http import require_GET

@require_GET
def download_file(request, pk):
    report = Report.objects.get(pk=pk)

    if report.user != request.user:
        return HttpResponse('Unauthorized', status=403)

    return FileResponse(
        report.file.open('rb'),
        as_attachment=True,
        filename=report.file.name
    )
```

**Upload:**
```python
from django.views.generic import FormView
from django.core.files.storage import default_storage

class FileUploadView(FormView):
    form_class = FileUploadForm

    def form_valid(self, form):
        file = form.cleaned_data['file']

        # Validate size/type
        if file.size > 10 * 1024 * 1024:
            form.add_error('file', 'File too large')
            return self.form_invalid(form)

        filename = default_storage.save(f'uploads/{file.name}', file)
        return super().form_valid(form)
```

### Workflow 4: Implement Pagination

**Template-based:**
```python
from django.core.paginator import Paginator

def article_list(request):
    articles = Article.objects.filter(published=True)
    paginator = Paginator(articles, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'articles.html', {'page_obj': page_obj})
```

**API (cursor-based):**
```python
def article_list_api(request):
    cursor = request.GET.get('cursor')
    limit = min(int(request.GET.get('limit', 20)), 100)

    queryset = Article.objects.filter(published=True).order_by('-id')
    if cursor:
        queryset = queryset.filter(id__lt=int(cursor))

    articles = list(queryset[:limit + 1])
    has_more = len(articles) > limit

    if has_more:
        articles = articles[:limit]
        next_cursor = articles[-1].id
    else:
        next_cursor = None

    return JsonResponse({
        'results': [{'id': a.id, 'title': a.title} for a in articles],
        'next_cursor': next_cursor,
    })
```

**See:** `reference/pagination.md` for all pagination strategies

### Workflow 5: Add View-Level Caching

**Cache entire view:**
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15 minutes
def article_list(request):
    articles = Article.objects.filter(published=True)
    return render(request, 'articles.html', {'articles': articles})
```

**Conditional caching (ETags):**
```python
from django.views.decorators.http import etag
import hashlib

def article_etag(request, slug):
    article = Article.objects.get(slug=slug)
    return hashlib.md5(f"{article.updated_at}".encode()).hexdigest()

@etag(article_etag)
def article_detail(request, slug):
    article = Article.objects.get(slug=slug)
    return render(request, 'detail.html', {'article': article})
```

**See:** `reference/caching.md` for cache invalidation patterns

## FBV vs CBV Decision Tree

```
Need to handle HTTP request?
│
├─ Simple, one-time logic? → FBV
│  └─ API endpoint, form handler, redirect
│
├─ CRUD operations? → CBV
│  └─ ListView, DetailView, CreateView, UpdateView, DeleteView
│
├─ Reusable behavior? → CBV with mixins
│  └─ LoginRequiredMixin, PermissionRequiredMixin
│
└─ Complex business logic? → FBV
   └─ CBVs can become hard to follow
```

**FBV Advantages:** Explicit control, easier to debug, simpler
**CBV Advantages:** Code reuse, DRY for CRUD, built-in pagination/forms

## Anti-Patterns

**1. Business logic in views:**
```python
# BAD
def create_order(request):
    order = Order.objects.create(user=request.user)
    # 50 lines of processing...

# GOOD
def create_order(request):
    order = Order.create_from_request(request)  # Model method
    return redirect('order-detail', pk=order.pk)
```

**2. Missing CSRF protection:**
```python
# BAD
@csrf_exempt
def api_create(request):  # No auth!
    ...

# GOOD
@login_required
def api_create(request):
    # Verify token/session
    ...
```

**3. N+1 queries:**
```python
# BAD
articles = Article.objects.all()
# Template: {{ article.author.name }} → N+1

# GOOD
articles = Article.objects.select_related('author').all()
```

**4. Exposing internal fields:**
```python
# BAD
return JsonResponse(model_to_dict(user))  # Exposes password!

# GOOD
return JsonResponse({'id': user.id, 'username': user.username})
```

## Security Considerations

**CSRF Protection:**
- All POST/PUT/DELETE need CSRF
- Use `@csrf_exempt` only with token auth
- Include `{% csrf_token %}` in forms

**Input Validation:**
```python
from django.core.validators import validate_email

email = request.POST.get('email')
validate_email(email)
```

**SQL Injection Prevention:**
```python
# SAFE
Article.objects.filter(title=user_input)

# UNSAFE
Article.objects.raw(f"SELECT * WHERE title = '{user_input}'")

# If raw SQL needed
Article.objects.raw("SELECT * WHERE title = %s", [user_input])
```

**Open Redirect Prevention:**
```python
from django.utils.http import url_has_allowed_host_and_scheme

next_url = request.GET.get('next', '/')
if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
    next_url = '/'
```

**File Upload Security:**
- Validate file types and sizes
- Store outside webroot
- Use `django.core.files.storage`
- Scan for malware if needed

## Scripts & Tools

### generate_view.py

Generate FBV or CBV with proper decorators and imports.

**Usage:**
```bash
# ListView
python scripts/generate_view.py --name ArticleListView --type list --model Article

# API view
python scripts/generate_view.py --name article_api --type api --method GET

# File upload
python scripts/generate_view.py --name upload --type file-upload

# Async view
python scripts/generate_view.py --name dashboard --type async
```

**Options:**
- `--type`: list, detail, create, update, delete, form, api, file-upload, file-download, async
- `--model`: Model name
- `--app`: App name
- `--method`: HTTP method (GET, POST, etc.)
- `--output`: Output file path
- `--with-tests`: Generate test code

## Related Skills

- **django-forms**: Form handling, validation, rendering
- **django-templates**: Template syntax, context processors
- **django-models**: QuerySet optimization, relationships
- **django-testing**: View testing, mocking
- **django-admin**: Custom admin views via `get_urls()`

## Django Version Notes

- **Django 4.1+**: Async views fully supported
- **Django 4.2+**: Psycopg 3 for async DB operations
- **Django 5.0+**: Simplified async middleware
- **Django 5.1+**: More async ORM operations

**Async requires:**
- ASGI server (Daphne, Uvicorn)
- Async-compatible middleware
- Async database backend

## Reference Files

- **`reference/cbv_mixins.md`** - Complete CBV mixin catalog with inheritance chains
- **`reference/url_patterns.md`** - URL routing, converters, namespacing
- **`reference/api_patterns.md`** - REST API patterns without DRF
- **`reference/pagination.md`** - Pagination strategies for templates and APIs
- **`reference/caching.md`** - View caching, ETags, cache invalidation
- **`reference/async_views.md`** - Async views, when to use, common pitfalls

## Troubleshooting

**CSRF verification failed:**
- Ensure `{% csrf_token %}` in forms
- Check `CSRF_TRUSTED_ORIGINS` in settings
- For APIs, use token auth

**TemplateDoesNotExist:**
- Check `TEMPLATES` settings
- Verify template path matches convention
- Use `DIRS` for custom locations

**Page not found (404):**
- Check URL pattern order (specific before generic)
- Verify `app_name` and namespace
- Use `reverse()` to debug

**Slow performance:**
- Use `django-debug-toolbar`
- Add `select_related()` / `prefetch_related()`
- Enable query logging
- Consider view caching

**View didn't return HttpResponse:**
- Ensure all paths return response
- Check for missing `return` statements
- Verify decorator order
