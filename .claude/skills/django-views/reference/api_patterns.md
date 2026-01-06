# REST API Patterns Without DRF

Building REST APIs with Django's built-in JsonResponse and view patterns, without Django REST Framework.

## Table of Contents

- [Basic JsonResponse Patterns](#basic-jsonresponse-patterns)
- [HTTP Status Codes](#http-status-codes)
- [Request Handling](#request-handling)
- [Error Handling](#error-handling)
- [Content Negotiation](#content-negotiation)
- [Authentication](#authentication)
- [Serialization Patterns](#serialization-patterns)
- [API Versioning](#api-versioning)
- [Rate Limiting](#rate-limiting)
- [Complete Examples](#complete-examples)

## Basic JsonResponse Patterns

### Simple GET Endpoint

```python
from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
def article_list(request):
    """List all published articles."""
    articles = Article.objects.filter(published=True).select_related('author')

    data = {
        'count': articles.count(),
        'results': [
            {
                'id': article.id,
                'title': article.title,
                'author': article.author.username,
                'created_at': article.created_at.isoformat(),
            }
            for article in articles
        ]
    }

    return JsonResponse(data)
```

### GET Single Object

```python
from django.shortcuts import get_object_or_404

@require_GET
def article_detail(request, pk):
    """Get single article."""
    article = get_object_or_404(
        Article.objects.select_related('author').prefetch_related('tags'),
        pk=pk
    )

    data = {
        'id': article.id,
        'title': article.title,
        'content': article.content,
        'author': {
            'id': article.author.id,
            'username': article.author.username,
        },
        'tags': [tag.name for tag in article.tags.all()],
        'created_at': article.created_at.isoformat(),
        'updated_at': article.updated_at.isoformat(),
    }

    return JsonResponse(data)
```

### POST to Create

```python
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt  # Only with token auth!
@require_POST
def article_create(request):
    """Create new article."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Invalid JSON'},
            status=400
        )

    # Validate required fields
    required_fields = ['title', 'content']
    missing = [f for f in required_fields if f not in data]
    if missing:
        return JsonResponse(
            {'error': f'Missing fields: {", ".join(missing)}'},
            status=400
        )

    # Create article
    article = Article.objects.create(
        title=data['title'],
        content=data['content'],
        author=request.user
    )

    return JsonResponse(
        {
            'id': article.id,
            'title': article.title,
            'created_at': article.created_at.isoformat(),
        },
        status=201
    )
```

### PUT/PATCH to Update

```python
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def article_update(request, pk):
    """Update article."""
    article = get_object_or_404(Article, pk=pk)

    # Permission check
    if article.author != request.user:
        return JsonResponse(
            {'error': 'Permission denied'},
            status=403
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Update fields
    if 'title' in data:
        article.title = data['title']
    if 'content' in data:
        article.content = data['content']

    article.save()

    return JsonResponse({
        'id': article.id,
        'title': article.title,
        'updated_at': article.updated_at.isoformat(),
    })
```

### DELETE

```python
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["DELETE"])
def article_delete(request, pk):
    """Delete article."""
    article = get_object_or_404(Article, pk=pk)

    # Permission check
    if article.author != request.user:
        return JsonResponse(
            {'error': 'Permission denied'},
            status=403
        )

    article.delete()

    return JsonResponse({'message': 'Article deleted'}, status=204)
```

## HTTP Status Codes

### Standard Codes

```python
# Success
200 - OK (GET, PUT, PATCH success)
201 - Created (POST success)
204 - No Content (DELETE success)

# Client Errors
400 - Bad Request (validation failed)
401 - Unauthorized (auth required)
403 - Forbidden (no permission)
404 - Not Found
405 - Method Not Allowed
409 - Conflict (e.g., duplicate)
422 - Unprocessable Entity (semantic errors)
429 - Too Many Requests (rate limit)

# Server Errors
500 - Internal Server Error
503 - Service Unavailable
```

### Usage Examples

```python
# 200 OK
return JsonResponse({'data': 'value'})

# 201 Created
return JsonResponse({'id': obj.id}, status=201)

# 204 No Content
return JsonResponse({}, status=204)

# 400 Bad Request
return JsonResponse({'error': 'Invalid input'}, status=400)

# 401 Unauthorized
return JsonResponse({'error': 'Authentication required'}, status=401)

# 403 Forbidden
return JsonResponse({'error': 'Permission denied'}, status=403)

# 404 Not Found
return JsonResponse({'error': 'Not found'}, status=404)

# 500 Internal Server Error
return JsonResponse({'error': 'Server error'}, status=500)
```

## Request Handling

### Parse JSON Body

```python
def parse_json_body(request):
    """Parse and validate JSON body."""
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None

def article_create(request):
    data = parse_json_body(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Process data
    ...
```

### Query Parameters

```python
def article_list(request):
    """List with filtering."""
    # Get query params
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    search = request.GET.get('search', '')
    category = request.GET.get('category')
    sort = request.GET.get('sort', '-created_at')

    # Build query
    queryset = Article.objects.filter(published=True)

    if search:
        queryset = queryset.filter(title__icontains=search)

    if category:
        queryset = queryset.filter(category_id=category)

    # Sort
    allowed_sorts = ['created_at', '-created_at', 'title', '-title']
    if sort in allowed_sorts:
        queryset = queryset.order_by(sort)

    # Paginate
    from django.core.paginator import Paginator
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    return JsonResponse({
        'count': paginator.count,
        'page': page_obj.number,
        'num_pages': paginator.num_pages,
        'results': [serialize_article(a) for a in page_obj],
    })
```

### Request Headers

```python
def api_view(request):
    # Content type
    content_type = request.content_type  # 'application/json'

    # Custom headers
    api_key = request.headers.get('X-API-Key')
    auth_token = request.headers.get('Authorization')

    # AJAX detection
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # User agent
    user_agent = request.headers.get('User-Agent')

    # Accept header (content negotiation)
    accept = request.headers.get('Accept', 'application/json')
```

## Error Handling

### Error Response Helper

```python
def error_response(message, status=400, **extra):
    """Standard error response format."""
    data = {'error': message}
    data.update(extra)
    return JsonResponse(data, status=status)

# Usage
return error_response('Invalid input', status=400)
return error_response('Not found', status=404, code='ARTICLE_NOT_FOUND')
```

### Validation Errors

```python
def article_create(request):
    data = parse_json_body(request)
    if not data:
        return error_response('Invalid JSON', status=400)

    # Field validation
    errors = {}

    if not data.get('title'):
        errors['title'] = 'This field is required'
    elif len(data['title']) > 200:
        errors['title'] = 'Title too long (max 200 characters)'

    if not data.get('content'):
        errors['content'] = 'This field is required'

    if errors:
        return JsonResponse({'errors': errors}, status=400)

    # Create article
    article = Article.objects.create(
        title=data['title'],
        content=data['content'],
        author=request.user
    )

    return JsonResponse(serialize_article(article), status=201)
```

### Exception Handler Decorator

```python
from functools import wraps
from django.db import IntegrityError

def api_exception_handler(view_func):
    """Catch exceptions and return JSON errors."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Article.DoesNotExist:
            return error_response('Article not found', status=404)
        except IntegrityError as e:
            return error_response(f'Database error: {str(e)}', status=409)
        except ValueError as e:
            return error_response(str(e), status=400)
        except Exception as e:
            # Log error
            import logging
            logger = logging.getLogger(__name__)
            logger.exception('API error')

            # Don't expose internal errors in production
            if settings.DEBUG:
                return error_response(str(e), status=500)
            else:
                return error_response('Internal server error', status=500)

    return wrapper

@api_exception_handler
def article_detail(request, pk):
    article = Article.objects.get(pk=pk)  # May raise DoesNotExist
    return JsonResponse(serialize_article(article))
```

## Content Negotiation

### Accept Multiple Formats

```python
def article_list(request):
    """Return JSON or XML based on Accept header."""
    articles = Article.objects.filter(published=True)

    # Check Accept header
    accept = request.headers.get('Accept', 'application/json')

    if 'application/xml' in accept:
        return xml_response(articles)
    elif 'text/csv' in accept:
        return csv_response(articles)
    else:
        return json_response(articles)

def json_response(articles):
    data = [serialize_article(a) for a in articles]
    return JsonResponse({'results': data})

def xml_response(articles):
    from django.http import HttpResponse
    import xml.etree.ElementTree as ET

    root = ET.Element('articles')
    for article in articles:
        elem = ET.SubElement(root, 'article')
        ET.SubElement(elem, 'id').text = str(article.id)
        ET.SubElement(elem, 'title').text = article.title

    xml_str = ET.tostring(root, encoding='unicode')
    return HttpResponse(xml_str, content_type='application/xml')

def csv_response(articles):
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="articles.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Title', 'Author'])
    for article in articles:
        writer.writerow([article.id, article.title, article.author.username])

    return response
```

### API Versioning in Accept Header

```python
def article_list(request):
    """Version via Accept header."""
    accept = request.headers.get('Accept', '')

    if 'application/vnd.myapi.v2+json' in accept:
        return article_list_v2(request)
    else:
        return article_list_v1(request)
```

## Authentication

### Token Authentication

```python
from django.contrib.auth import get_user_model
import hmac
import hashlib

User = get_user_model()

def verify_token(token):
    """Verify JWT-like token."""
    # Simplified - use python-jwt in production
    try:
        user_id, signature = token.split(':')
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode(),
            user_id.encode(),
            hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(signature, expected_sig):
            return User.objects.get(id=int(user_id))
    except:
        pass
    return None

def token_required(view_func):
    """Decorator for token authentication."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return error_response('Missing token', status=401)

        token = auth_header[7:]  # Remove 'Bearer '
        user = verify_token(token)

        if not user:
            return error_response('Invalid token', status=401)

        request.user = user
        return view_func(request, *args, **kwargs)

    return wrapper

@token_required
def article_create(request):
    # request.user is authenticated
    article = Article.objects.create(
        title=request.POST['title'],
        author=request.user
    )
    return JsonResponse(serialize_article(article), status=201)
```

### API Key Authentication

```python
def api_key_required(view_func):
    """Decorator for API key authentication."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        api_key = request.headers.get('X-API-Key')

        if not api_key:
            return error_response('API key required', status=401)

        try:
            api_token = APIToken.objects.select_related('user').get(
                key=api_key,
                is_active=True
            )
        except APIToken.DoesNotExist:
            return error_response('Invalid API key', status=401)

        # Check rate limit
        if api_token.is_rate_limited():
            return error_response('Rate limit exceeded', status=429)

        request.user = api_token.user
        request.api_token = api_token
        return view_func(request, *args, **kwargs)

    return wrapper
```

## Serialization Patterns

### Model Serializer Function

```python
def serialize_article(article, include_content=False):
    """Serialize article to dict."""
    data = {
        'id': article.id,
        'title': article.title,
        'slug': article.slug,
        'author': {
            'id': article.author.id,
            'username': article.author.username,
        },
        'created_at': article.created_at.isoformat(),
        'updated_at': article.updated_at.isoformat(),
    }

    if include_content:
        data['content'] = article.content

    return data

def article_list(request):
    articles = Article.objects.select_related('author')
    return JsonResponse({
        'results': [serialize_article(a) for a in articles]
    })

def article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk)
    return JsonResponse(serialize_article(article, include_content=True))
```

### Serializer Class Pattern

```python
class ArticleSerializer:
    """Serialize article instances."""

    def __init__(self, instance, include_content=False):
        self.instance = instance
        self.include_content = include_content

    def data(self):
        """Return serialized data."""
        article = self.instance
        data = {
            'id': article.id,
            'title': article.title,
            'author': self.serialize_user(article.author),
            'created_at': article.created_at.isoformat(),
        }

        if self.include_content:
            data['content'] = article.content

        return data

    def serialize_user(self, user):
        return {
            'id': user.id,
            'username': user.username,
        }

# Usage
def article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk)
    serializer = ArticleSerializer(article, include_content=True)
    return JsonResponse(serializer.data())
```

### Handle Related Objects

```python
def serialize_article_with_relations(article):
    """Serialize with tags and comments."""
    return {
        'id': article.id,
        'title': article.title,
        'author': {
            'id': article.author.id,
            'username': article.author.username,
        },
        'tags': [
            {'id': tag.id, 'name': tag.name}
            for tag in article.tags.all()
        ],
        'comments': [
            {
                'id': c.id,
                'text': c.text,
                'author': c.author.username,
            }
            for c in article.comments.select_related('author').all()
        ],
        'created_at': article.created_at.isoformat(),
    }

def article_detail(request, pk):
    article = get_object_or_404(
        Article.objects.prefetch_related('tags', 'comments__author'),
        pk=pk
    )
    return JsonResponse(serialize_article_with_relations(article))
```

## API Versioning

### URL-Based Versioning

```python
# urls.py
urlpatterns = [
    path('api/v1/articles/', views.article_list_v1),
    path('api/v2/articles/', views.article_list_v2),
]

# views.py
def article_list_v1(request):
    """V1: Simple format."""
    articles = Article.objects.all()
    return JsonResponse({
        'results': [
            {'id': a.id, 'title': a.title}
            for a in articles
        ]
    })

def article_list_v2(request):
    """V2: Extended format with author."""
    articles = Article.objects.select_related('author')
    return JsonResponse({
        'results': [
            {
                'id': a.id,
                'title': a.title,
                'author': a.author.username,
            }
            for a in articles
        ]
    })
```

### Header-Based Versioning

```python
def article_list(request):
    """Route by API-Version header."""
    version = request.headers.get('API-Version', '1')

    if version == '2':
        return article_list_v2(request)
    else:
        return article_list_v1(request)
```

## Rate Limiting

### Simple Rate Limiter

```python
from django.core.cache import cache
from django.utils import timezone

def rate_limit(max_requests=100, window=3600):
    """Rate limit decorator."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Use IP or user ID as key
            if request.user.is_authenticated:
                key = f'rate_limit_user_{request.user.id}'
            else:
                key = f'rate_limit_ip_{request.META.get("REMOTE_ADDR")}'

            # Get current count
            count = cache.get(key, 0)

            if count >= max_requests:
                return JsonResponse(
                    {'error': 'Rate limit exceeded'},
                    status=429
                )

            # Increment
            cache.set(key, count + 1, window)

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator

@rate_limit(max_requests=100, window=3600)
def article_list(request):
    articles = Article.objects.all()
    return JsonResponse({'results': [...]})
```

## Complete Examples

### Full CRUD API

```python
# api/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import json

# Helper functions
def parse_json_body(request):
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None

def error_response(message, status=400):
    return JsonResponse({'error': message}, status=status)

def serialize_article(article):
    return {
        'id': article.id,
        'title': article.title,
        'content': article.content,
        'author': article.author.username,
        'created_at': article.created_at.isoformat(),
    }

# Views
@require_http_methods(["GET"])
def article_list(request):
    """List all articles."""
    articles = Article.objects.filter(
        published=True
    ).select_related('author')

    return JsonResponse({
        'count': articles.count(),
        'results': [serialize_article(a) for a in articles]
    })

@require_http_methods(["GET"])
def article_detail(request, pk):
    """Get single article."""
    article = get_object_or_404(Article, pk=pk)
    return JsonResponse(serialize_article(article))

@csrf_exempt  # Use proper auth in production
@require_http_methods(["POST"])
def article_create(request):
    """Create article."""
    data = parse_json_body(request)
    if not data:
        return error_response('Invalid JSON', status=400)

    # Validate
    if not data.get('title'):
        return error_response('Title required', status=400)

    # Create
    article = Article.objects.create(
        title=data['title'],
        content=data.get('content', ''),
        author=request.user
    )

    return JsonResponse(serialize_article(article), status=201)

@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def article_update(request, pk):
    """Update article."""
    article = get_object_or_404(Article, pk=pk)

    if article.author != request.user:
        return error_response('Permission denied', status=403)

    data = parse_json_body(request)
    if not data:
        return error_response('Invalid JSON', status=400)

    # Update
    if 'title' in data:
        article.title = data['title']
    if 'content' in data:
        article.content = data['content']

    article.save()
    return JsonResponse(serialize_article(article))

@csrf_exempt
@require_http_methods(["DELETE"])
def article_delete(request, pk):
    """Delete article."""
    article = get_object_or_404(Article, pk=pk)

    if article.author != request.user:
        return error_response('Permission denied', status=403)

    article.delete()
    return JsonResponse({}, status=204)
```

### URLs

```python
# api/urls.py
from django.urls import path
from . import views

app_name = 'api'
urlpatterns = [
    path('articles/', views.article_list, name='article-list'),
    path('articles/<int:pk>/', views.article_detail, name='article-detail'),
    path('articles/create/', views.article_create, name='article-create'),
    path('articles/<int:pk>/update/', views.article_update, name='article-update'),
    path('articles/<int:pk>/delete/', views.article_delete, name='article-delete'),
]
```
