#!/usr/bin/env python3
"""
Generate Django views based on requirements.

Usage:
    python generate_view.py --name ArticleListView --type list --model Article --app blog
    python generate_view.py --name article_api --type api --method GET
    python generate_view.py --name upload --type file-upload
"""

import argparse
import sys
from pathlib import Path


# View templates
TEMPLATES = {
    'list': '''from django.views.generic import ListView
from {app}.models import {model}


class {name}(ListView):
    """List {model_plural}."""
    model = {model}
    template_name = '{app}/{template_name}'
    context_object_name = '{context_name}'
    paginate_by = 25
    ordering = ['-created_at']

    def get_queryset(self):
        """Optimize and filter queryset."""
        qs = super().get_queryset()
        return qs.select_related('author').filter(published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add extra context here
        return context
''',

    'detail': '''from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from {app}.models import {model}


class {name}(DetailView):
    """Display single {model}."""
    model = {model}
    template_name = '{app}/{template_name}'
    context_object_name = '{context_name}'

    def get_queryset(self):
        """Optimize queries."""
        return super().get_queryset().select_related(
            'author'
        ).prefetch_related('tags')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add related data here
        return context
''',

    'create': '''from django.views.generic import CreateView
from django.urls import reverse_lazy
from {app}.models import {model}
from {app}.forms import {model}Form


class {name}(CreateView):
    """Create new {model}."""
    model = {model}
    form_class = {model}Form
    template_name = '{app}/{template_name}'
    success_url = reverse_lazy('{app}:{model_lower}-list')

    def form_valid(self, form):
        """Set additional fields before saving."""
        form.instance.author = self.request.user
        return super().form_valid(form)
''',

    'update': '''from django.views.generic import UpdateView
from django.urls import reverse_lazy
from {app}.models import {model}
from {app}.forms import {model}Form


class {name}(UpdateView):
    """Update existing {model}."""
    model = {model}
    form_class = {model}Form
    template_name = '{app}/{template_name}'

    def get_queryset(self):
        """Only allow editing own objects."""
        qs = super().get_queryset()
        return qs.filter(author=self.request.user)

    def get_success_url(self):
        """Redirect to detail page."""
        from django.urls import reverse
        return reverse('{app}:{model_lower}-detail', kwargs={{'pk': self.object.pk}})
''',

    'delete': '''from django.views.generic import DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from {app}.models import {model}


class {name}(DeleteView):
    """Delete {model} with confirmation."""
    model = {model}
    template_name = '{app}/{template_name}'
    success_url = reverse_lazy('{app}:{model_lower}-list')

    def get_queryset(self):
        """Only allow deleting own objects."""
        qs = super().get_queryset()
        return qs.filter(author=self.request.user)

    def delete(self, request, *args, **kwargs):
        """Add success message."""
        messages.success(request, '{model} deleted successfully')
        return super().delete(request, *args, **kwargs)
''',

    'form': '''from django.views.generic import FormView
from django.urls import reverse_lazy
from {app}.forms import {form_class}


class {name}(FormView):
    """Handle form submission."""
    template_name = '{app}/{template_name}'
    form_class = {form_class}
    success_url = reverse_lazy('{app}:success')

    def form_valid(self, form):
        """Process valid form."""
        # Process form data
        form.send_email()
        return super().form_valid(form)

    def get_initial(self):
        """Set initial form data."""
        initial = super().get_initial()
        if self.request.user.is_authenticated:
            initial['email'] = self.request.user.email
        return initial
''',

    'api': '''from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from {app}.models import {model}
import json


@require_http_methods(["{method}"])
def {name}(request{params}):
    """API endpoint for {model}."""
    {body}
''',

    'api-list': '''articles = {model}.objects.filter(published=True).select_related('author')

    return JsonResponse({{
        'count': articles.count(),
        'results': [
            {{
                'id': obj.id,
                'title': obj.title,
                'created_at': obj.created_at.isoformat(),
            }}
            for obj in articles
        ]
    }})''',

    'api-detail': '''obj = get_object_or_404({model}, pk=pk)

    return JsonResponse({{
        'id': obj.id,
        'title': obj.title,
        'created_at': obj.created_at.isoformat(),
    }})''',

    'api-create': '''try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({{'error': 'Invalid JSON'}}, status=400)

    # Validate required fields
    required = ['title', 'content']
    missing = [f for f in required if f not in data]
    if missing:
        return JsonResponse(
            {{'error': f'Missing fields: {{", ".join(missing)}}'}},
            status=400
        )

    # Create object
    obj = {model}.objects.create(
        title=data['title'],
        content=data['content'],
        author=request.user
    )

    return JsonResponse(
        {{'id': obj.id, 'title': obj.title}},
        status=201
    )''',

    'file-upload': '''from django.views.generic import FormView
from django.core.files.storage import default_storage
from {app}.forms import FileUploadForm


class {name}(FormView):
    """Handle file uploads."""
    template_name = '{app}/{template_name}'
    form_class = FileUploadForm
    success_url = reverse_lazy('{app}:success')

    def form_valid(self, form):
        """Process uploaded file."""
        file = form.cleaned_data['file']

        # Validate file size (10MB max)
        if file.size > 10 * 1024 * 1024:
            form.add_error('file', 'File too large (max 10MB)')
            return self.form_invalid(form)

        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
        if file.content_type not in allowed_types:
            form.add_error('file', 'Invalid file type')
            return self.form_invalid(form)

        # Save file
        filename = default_storage.save(
            f'uploads/{{file.name}}',
            file
        )

        # Create database record
        from {app}.models import Document
        Document.objects.create(
            file=filename,
            uploaded_by=self.request.user
        )

        return super().form_valid(form)
''',

    'file-download': '''from django.http import FileResponse, HttpResponse
from django.views.decorators.http import require_GET
from django.shortcuts import get_object_or_404
from {app}.models import {model}
import mimetypes


@require_GET
def {name}(request, pk):
    """Download file."""
    obj = get_object_or_404({model}, pk=pk)

    # Permission check
    if obj.user != request.user:
        return HttpResponse('Unauthorized', status=403)

    # Stream file
    response = FileResponse(
        obj.file.open('rb'),
        as_attachment=True,
        filename=obj.file.name
    )

    # Set content type
    content_type, _ = mimetypes.guess_type(obj.file.name)
    if content_type:
        response['Content-Type'] = content_type

    return response
''',

    'async': '''from django.http import JsonResponse
import httpx
import asyncio


async def {name}(request):
    """Async view with parallel API calls."""
    async with httpx.AsyncClient() as client:
        # Fetch from multiple APIs in parallel
        results = await asyncio.gather(
            client.get('https://api1.example.com/data'),
            client.get('https://api2.example.com/data'),
            client.get('https://api3.example.com/data'),
        )

    return JsonResponse({{
        'api1': results[0].json(),
        'api2': results[1].json(),
        'api3': results[2].json(),
    }})
''',
}


def pluralize(word):
    """Simple pluralization."""
    if word.endswith('y'):
        return word[:-1] + 'ies'
    elif word.endswith('s'):
        return word + 'es'
    else:
        return word + 's'


def to_snake_case(name):
    """Convert CamelCase to snake_case."""
    import re
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def generate_view(args):
    """Generate view code based on arguments."""
    # Determine view type
    view_type = args.type

    if view_type not in TEMPLATES:
        print(f"Error: Unknown view type '{view_type}'")
        print(f"Available types: {', '.join(TEMPLATES.keys())}")
        return 1

    # Build context
    context = {
        'name': args.name,
        'app': args.app or 'myapp',
        'model': args.model or 'Article',
    }

    # Add computed values
    context['model_lower'] = context['model'].lower()
    context['model_plural'] = pluralize(context['model'])
    context['context_name'] = pluralize(context['model_lower'])

    # Template name
    if view_type in ['list', 'detail', 'create', 'update', 'delete', 'form', 'file-upload']:
        if view_type == 'create' or view_type == 'update':
            template_name = f"{context['model_lower']}_form.html"
        elif view_type == 'delete':
            template_name = f"{context['model_lower']}_confirm_delete.html"
        elif view_type == 'form' or view_type == 'file-upload':
            template_name = f"{to_snake_case(args.name)}.html"
        else:
            template_name = f"{context['model_lower']}_{view_type}.html"
        context['template_name'] = template_name

    # Form class
    if view_type == 'form' or view_type == 'file-upload':
        context['form_class'] = args.form_class or f"{context['model']}Form"

    # API specific
    if view_type == 'api':
        context['method'] = args.method or 'GET'

        # Determine API body based on method
        if context['method'] == 'GET':
            if args.detail:
                context['params'] = ', pk'
                body_template = TEMPLATES['api-detail']
            else:
                context['params'] = ''
                body_template = TEMPLATES['api-list']
        elif context['method'] == 'POST':
            context['params'] = ''
            body_template = TEMPLATES['api-create']
        else:
            context['params'] = ''
            body_template = '# Implement your logic here\n    pass'

        # Format body template first
        context['body'] = body_template.format(**context)

        # Add csrf_exempt for non-GET
        if context['method'] != 'GET':
            template = TEMPLATES[view_type]
            template = template.replace(
                '@require_http_methods',
                '@csrf_exempt\n@require_http_methods'
            )
            code = template.format(**context)
        else:
            code = TEMPLATES[view_type].format(**context)
    else:
        # Generate code
        code = TEMPLATES[view_type].format(**context)

    # Output
    if args.output:
        # Write to file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(code)

        print(f"View written to: {output_path}")
    else:
        # Print to stdout
        print(code)

    # Generate URL pattern
    print("\n# Add to urls.py:")
    generate_url_pattern(args, context)

    # Generate test
    if args.with_tests:
        print("\n# Test code:")
        generate_test(args, context)

    return 0


def generate_url_pattern(args, context):
    """Generate URL pattern for the view."""
    view_type = args.type

    if view_type in ['list', 'detail', 'create', 'update', 'delete', 'form', 'file-upload']:
        # CBV
        print(f"from django.urls import path")
        print(f"from . import views\n")

        if view_type == 'list':
            print(f"path('', views.{context['name']}.as_view(), name='{context['model_lower']}-list'),")
        elif view_type == 'detail':
            print(f"path('<int:pk>/', views.{context['name']}.as_view(), name='{context['model_lower']}-detail'),")
        elif view_type == 'create':
            print(f"path('create/', views.{context['name']}.as_view(), name='{context['model_lower']}-create'),")
        elif view_type == 'update':
            print(f"path('<int:pk>/edit/', views.{context['name']}.as_view(), name='{context['model_lower']}-update'),")
        elif view_type == 'delete':
            print(f"path('<int:pk>/delete/', views.{context['name']}.as_view(), name='{context['model_lower']}-delete'),")
        else:
            print(f"path('{to_snake_case(context['name'])}/', views.{context['name']}.as_view(), name='{to_snake_case(context['name'])}'),")

    elif view_type == 'api':
        # FBV
        print(f"from django.urls import path")
        print(f"from . import views\n")

        if args.detail:
            print(f"path('api/{context['model_lower']}/<int:pk>/', views.{context['name']}, name='api-{context['model_lower']}-detail'),")
        else:
            print(f"path('api/{context['model_lower']}/', views.{context['name']}, name='api-{context['model_lower']}-list'),")

    elif view_type in ['file-download', 'async']:
        # FBV
        print(f"from django.urls import path")
        print(f"from . import views\n")
        print(f"path('{to_snake_case(context['name'])}/', views.{context['name']}, name='{to_snake_case(context['name'])}'),")


def generate_test(args, context):
    """Generate test code."""
    view_type = args.type

    if view_type == 'list':
        print(f'''from django.test import TestCase
from django.urls import reverse
from {context['app']}.models import {context['model']}


class {context['name']}Test(TestCase):
    def test_list_view(self):
        """Test {context['model']} list view."""
        # Create test data
        {context['model']}.objects.create(title='Test', published=True)

        # Access view
        url = reverse('{context['app']}:{context['model_lower']}-list')
        response = self.client.get(url)

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test')
        self.assertEqual(len(response.context['{context['context_name']}']), 1)
''')

    elif view_type == 'api':
        print(f'''from django.test import TestCase
from django.urls import reverse
from {context['app']}.models import {context['model']}
import json


class {context['name']}Test(TestCase):
    def test_api_view(self):
        """Test API endpoint."""
        # Create test data
        {context['model']}.objects.create(title='Test', published=True)

        # Access API
        url = reverse('{context['app']}:api-{context['model_lower']}-list')
        response = self.client.get(url)

        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['results']), 1)
''')


def main():
    parser = argparse.ArgumentParser(
        description='Generate Django views from templates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Generate ListView
  %(prog)s --name ArticleListView --type list --model Article --app blog

  # Generate DetailView
  %(prog)s --name ArticleDetailView --type detail --model Article --app blog

  # Generate API endpoint
  %(prog)s --name article_list_api --type api --method GET --model Article --app blog

  # Generate file upload view
  %(prog)s --name FileUploadView --type file-upload --app documents

  # Generate async view
  %(prog)s --name dashboard_async --type async --app dashboard
        '''
    )

    parser.add_argument('--name', required=True, help='View name (e.g., ArticleListView)')
    parser.add_argument('--type', required=True,
                        choices=['list', 'detail', 'create', 'update', 'delete',
                                 'form', 'api', 'file-upload', 'file-download', 'async'],
                        help='View type')
    parser.add_argument('--model', help='Model name (e.g., Article)')
    parser.add_argument('--app', help='App name (e.g., blog)')
    parser.add_argument('--method', choices=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
                        help='HTTP method (for API views)')
    parser.add_argument('--detail', action='store_true',
                        help='Generate detail endpoint (requires pk)')
    parser.add_argument('--form-class', help='Form class name')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--with-tests', action='store_true',
                        help='Generate test code')

    args = parser.parse_args()

    # Validation
    if args.type in ['list', 'detail', 'create', 'update', 'delete'] and not args.model:
        parser.error(f"--model is required for {args.type} views")

    if args.type == 'api' and not args.method:
        parser.error("--method is required for API views")

    return generate_view(args)


if __name__ == '__main__':
    sys.exit(main())
