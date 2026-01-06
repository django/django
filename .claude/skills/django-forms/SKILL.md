# Django Forms Skill

## Overview

This skill helps you create, validate, and render Django forms with proper security, accessibility, and frontend integration. Django forms handle user input validation, data cleaning, CSRF protection, and HTML rendering.

**When to use this skill:**
- Creating forms for data entry and validation
- Building ModelForms from Django models
- Implementing complex validation logic (cross-field, conditional)
- Handling file uploads securely
- Integrating forms with CSS frameworks (Bootstrap, Tailwind)
- Adding AJAX form submission
- Creating formsets for multiple object editing
- Ensuring form accessibility (WCAG compliance)

## Quick Start

**Create a ModelForm in 3 steps:**

```python
# 1. Define the form (forms.py)
from django import forms
from .models import Article

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'content', 'published']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
        }

# 2. Use in view (views.py)
def create_article(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('article_list')
    else:
        form = ArticleForm()
    return render(request, 'article_form.html', {'form': form})

# 3. Render in template (article_form.html)
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Save</button>
</form>
```

## When to Use This Skill

### Form vs ModelForm Decision Tree

```
Does your form save data to a model?
├─ YES → Use ModelForm
│  └─ Need custom validation?
│     ├─ Field-level → Override clean_<fieldname>()
│     └─ Cross-field → Override clean()
│
└─ NO → Use Form
   ├─ Login, search, contact forms
   ├─ API parameter validation
   └─ Multi-step wizards
```

### Common Use Cases

| Scenario | Solution |
|----------|----------|
| Single model CRUD | ModelForm with Meta.fields |
| File upload | FileField/ImageField with validation |
| Multiple related objects | Formsets (inline or standalone) |
| Frontend framework integration | Form with JSON response + AJAX |
| Complex validation | Custom clean() methods |
| Dynamic fields | Override __init__() to modify fields |

## Core Workflows

### Workflow 1: Create ModelForm with Validation

```python
from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    agree_to_terms = forms.BooleanField(required=True)

    class Meta:
        model = Product
        fields = ['name', 'price', 'description', 'category']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'min': '0', 'step': '0.01'})
        }

    def clean_price(self):
        """Field-level validation."""
        price = self.cleaned_data.get('price')
        if price and price < 0:
            raise forms.ValidationError('Price cannot be negative.')
        return price

    def clean_name(self):
        """Check uniqueness."""
        name = self.cleaned_data.get('name')
        qs = Product.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Product name already exists.')
        return name
```

**View usage:**
```python
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm()
    return render(request, 'products/form.html', {'form': form})
```

### Workflow 2: Add Cross-Field Validation

```python
from django import forms
from datetime import date

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'start_date', 'end_date', 'is_online', 'venue', 'meeting_link']

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_online = cleaned_data.get('is_online')

        # Validate date range
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError('End date must be after start date.')

        # Conditional field requirements
        if is_online and not cleaned_data.get('meeting_link'):
            self.add_error('meeting_link', 'Required for online events.')
        elif not is_online and not cleaned_data.get('venue'):
            self.add_error('venue', 'Required for in-person events.')

        return cleaned_data
```

**Key patterns:**
- Use `raise forms.ValidationError()` for general form errors
- Use `self.add_error('field', 'message')` for field-specific errors
- Always return `cleaned_data` at the end

### Workflow 3: Handle File Uploads Securely

```python
from django import forms
from django.core.validators import FileExtensionValidator
import magic

def validate_file_size(file):
    """Limit file size to 5MB."""
    if file.size > 5 * 1024 * 1024:
        raise forms.ValidationError('File size cannot exceed 5MB.')

def validate_image_mime_type(file):
    """Verify actual MIME type."""
    valid_mime_types = ['image/jpeg', 'image/png', 'image/gif']
    file_mime = magic.from_buffer(file.read(1024), mime=True)
    file.seek(0)
    if file_mime not in valid_mime_types:
        raise forms.ValidationError(f'Invalid file type: {file_mime}')

class ProfileForm(forms.ModelForm):
    avatar = forms.ImageField(
        required=False,
        validators=[
            validate_file_size,
            validate_image_mime_type,
            FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif'])
        ]
    )

    class Meta:
        model = Profile
        fields = ['avatar', 'bio']
```

**Template:**
```html
<form method="post" enctype="multipart/form-data">  <!-- Required! -->
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Update</button>
</form>
```

**See:** `/home/user/django/.claude/skills/django-forms/reference/file_uploads.md`

### Workflow 4: Create Formsets

```python
from django.forms import inlineformset_factory
from .models import Order, OrderItem

OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    fields=['product', 'quantity', 'price'],
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)

def order_update(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        formset = OrderItemFormSet(request.POST, instance=order)
        if formset.is_valid():
            formset.save()
            return redirect('order_detail', pk=order.pk)
    else:
        formset = OrderItemFormSet(instance=order)

    return render(request, 'order_form.html', {'order': order, 'formset': formset})
```

**Template:**
```html
<form method="post">
  {% csrf_token %}
  {{ formset.management_form }}  <!-- Required! -->

  {% for form in formset %}
    {{ form.as_p }}
  {% endfor %}

  <button type="submit">Save</button>
</form>
```

### Workflow 5: AJAX Form Submission

**Django View:**
```python
from django.http import JsonResponse

def contact_submit(request):
    form = ContactForm(request.POST)

    if form.is_valid():
        contact = form.save()
        return JsonResponse({
            'success': True,
            'message': 'Form submitted successfully!'
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors,
        }, status=400)
```

**JavaScript (Fetch API):**
```javascript
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.getElementById('contact-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(e.target);
    const csrftoken = getCookie('csrftoken');

    try {
        const response = await fetch('/api/contact/', {
            method: 'POST',
            headers: {'X-CSRFToken': csrftoken},
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            alert(data.message);
            e.target.reset();
        } else {
            displayErrors(data.errors);
        }
    } catch (error) {
        console.error('Error:', error);
    }
});

function displayErrors(errors) {
    for (const [field, messages] of Object.entries(errors)) {
        const input = document.querySelector(`[name="${field}"]`);
        if (input) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.textContent = messages.join(', ');
            input.parentNode.appendChild(errorDiv);
        }
    }
}
```

**See:** `/home/user/django/.claude/skills/django-forms/reference/ajax_patterns.md`

## Scripts & Tools

### Generate Form Script

Generate a ModelForm from a Django model:

```bash
python /home/user/django/.claude/skills/django-forms/scripts/generate_form.py \
    --model myapp.Product \
    --output myapp/forms.py
```

**Options:**
- `--fields name,price,description` - Include only specific fields
- `--exclude created_at,updated_at` - Exclude specific fields

### Accessibility Checker

Check form templates for accessibility issues:

```bash
python /home/user/django/.claude/skills/django-forms/scripts/accessibility_check.py \
    templates/forms/
```

**Checks for:**
- Missing labels
- Missing ARIA attributes
- Missing required indicators
- Improper button types
- Missing fieldset/legend

## Anti-Patterns

### 1. Validating in Views Instead of Forms

**Bad:**
```python
def create_product(request):
    name = request.POST.get('name')
    if not name:
        return render(request, 'form.html', {'error': 'Name required'})
```

**Good:**
```python
form = ProductForm(request.POST)
if form.is_valid():
    form.save()
```

### 2. Not Using commit=False

**Bad:**
```python
product = form.save()  # Already saved
product.created_by = request.user
product.save()  # Saves twice
```

**Good:**
```python
product = form.save(commit=False)
product.created_by = request.user
product.save()
```

### 3. Ignoring CSRF Protection

**Never do this:**
```python
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt  # DANGEROUS!
def my_form_view(request):
    pass
```

### 4. Manual HTML Without Form Rendering

**Avoid:**
```html
<input type="text" name="title">  <!-- No error handling, attributes -->
```

**Prefer:**
```html
{{ form.title }}  <!-- Includes errors, attributes, accessibility -->
```

## Security Considerations

### CSRF Protection

Always include `{% csrf_token %}` in POST forms:

```html
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Submit</button>
</form>
```

**For AJAX:**
```javascript
headers: {'X-CSRFToken': csrftoken}
```

### XSS Prevention

Django auto-escapes template variables:
```django
{{ form.title.value }}  <!-- Automatically escaped -->
```

### File Upload Security

**Key practices:**
1. Validate file extensions AND MIME types
2. Limit file sizes
3. Sanitize filenames
4. Store outside web root
5. Scan for malware in production

**See:** `/home/user/django/.claude/skills/django-forms/reference/file_uploads.md`

### SQL Injection Prevention

Forms + ORM = automatic protection:
```python
Product.objects.filter(name=form.cleaned_data['name'])  # Safe
```

## Reference Files

- **Field Types:** `/home/user/django/.claude/skills/django-forms/reference/field_types.md` - All form field types, widgets, validation options
- **Validation:** `/home/user/django/.claude/skills/django-forms/reference/validation.md` - Field-level, form-level, cross-field validation patterns
- **Widgets:** `/home/user/django/.claude/skills/django-forms/reference/widgets.md` - Widget customization, CSS/JS handling
- **CSS Frameworks:** `/home/user/django/.claude/skills/django-forms/reference/css_frameworks.md` - Bootstrap, Tailwind integration, accessibility
- **AJAX Patterns:** `/home/user/django/.claude/skills/django-forms/reference/ajax_patterns.md` - Fetch API, htmx, real-time validation
- **File Uploads:** `/home/user/django/.claude/skills/django-forms/reference/file_uploads.md` - File validation, security, image processing

## Related Skills

- **django-models** - Define models for ModelForms
- **django-views** - Handle form submission in views
- **django-templates** - Render forms in templates
- **django-admin** - Admin uses Django forms internally
- **django-testing** - Test form validation

## Django Version Notes

- **Django 4.1+**: Async form validation not yet supported
- **Django 4.0+**: Template-based widget rendering, formset validation improvements
- **Django 3.2+**: LTS version, stable form API
- **Django 5.0+**: Improved error messages, better accessibility defaults
