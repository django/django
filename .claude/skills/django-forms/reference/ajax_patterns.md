# AJAX Form Patterns Reference

Complete guide to submitting Django forms via AJAX with Fetch API, htmx, and proper error handling.

## Table of Contents

- [Fetch API Patterns](#fetch-api-patterns)
- [CSRF Token Handling](#csrf-token-handling)
- [Error Response Formatting](#error-response-formatting)
- [htmx Integration](#htmx-integration)
- [Real-time Validation](#real-time-validation)
- [File Upload via AJAX](#file-upload-via-ajax)

## Fetch API Patterns

### Basic AJAX Form Submission

**Django View:**
```python
# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .forms import ContactForm

@require_http_methods(["POST"])
def contact_submit(request):
    form = ContactForm(request.POST)

    if form.is_valid():
        # Process form
        contact = form.save()

        return JsonResponse({
            'success': True,
            'message': 'Form submitted successfully!',
            'data': {
                'id': contact.id,
                'name': contact.name,
                'email': contact.email,
            }
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors,
        }, status=400)
```

**JavaScript (Fetch API):**
```javascript
// Get CSRF token from cookie
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

const csrftoken = getCookie('csrftoken');

// Submit form
document.getElementById('contact-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
            },
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            // Success handling
            showSuccessMessage(data.message);
            form.reset();
        } else {
            // Error handling
            displayErrors(data.errors);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An unexpected error occurred.');
    }
});

function displayErrors(errors) {
    // Clear previous errors
    document.querySelectorAll('.error-message').forEach(el => el.remove());

    // Display new errors
    for (const [field, messages] of Object.entries(errors)) {
        const input = document.querySelector(`[name="${field}"]`);
        if (input) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message text-danger';
            errorDiv.textContent = messages.join(', ');
            input.parentNode.appendChild(errorDiv);
            input.classList.add('is-invalid');
        }
    }
}

function showSuccessMessage(message) {
    const alert = document.createElement('div');
    alert.className = 'alert alert-success';
    alert.textContent = message;
    document.getElementById('messages').appendChild(alert);

    // Auto-dismiss after 3 seconds
    setTimeout(() => alert.remove(), 3000);
}
```

### JSON Form Submission

**Django View:**
```python
import json
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt  # Don't use in production!

@require_http_methods(["POST"])
def api_contact_submit(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    form = ContactForm(data)

    if form.is_valid():
        contact = form.save()
        return JsonResponse({
            'success': True,
            'id': contact.id,
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors,
        }, status=400)
```

**JavaScript:**
```javascript
document.getElementById('contact-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    // Convert FormData to JSON
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            console.log('Form submitted:', result);
        } else {
            displayErrors(result.errors);
        }
    } catch (error) {
        console.error('Error:', error);
    }
});
```

## CSRF Token Handling

### Method 1: From Cookie

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

const csrftoken = getCookie('csrftoken');

// Use in fetch
fetch(url, {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrftoken,
    },
    body: formData
});
```

### Method 2: From Hidden Input

```javascript
// From {% csrf_token %} hidden input
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

fetch(url, {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrftoken,
    },
    body: formData
});
```

### Method 3: From Meta Tag

**HTML:**
```html
<meta name="csrf-token" content="{{ csrf_token }}">
```

**JavaScript:**
```javascript
const csrftoken = document.querySelector('meta[name="csrf-token"]').content;
```

### Method 4: Django Endpoint

**View:**
```python
from django.middleware.csrf import get_token
from django.http import JsonResponse

def get_csrf_token(request):
    return JsonResponse({'csrfToken': get_token(request)})
```

**JavaScript:**
```javascript
// Fetch CSRF token on page load
let csrftoken = null;

async function initCSRF() {
    const response = await fetch('/api/csrf-token/');
    const data = await response.json();
    csrftoken = data.csrfToken;
}

initCSRF();
```

## Error Response Formatting

### Structured Error Response

**Django View:**
```python
from django.http import JsonResponse
from django.core.exceptions import ValidationError

def structured_error_response(form):
    """Return structured error response."""
    errors = {
        'field_errors': {},
        'non_field_errors': [],
    }

    # Field-specific errors
    for field, error_list in form.errors.items():
        if field == '__all__':
            errors['non_field_errors'] = error_list
        else:
            errors['field_errors'][field] = {
                'messages': error_list,
                'label': form.fields[field].label,
            }

    return JsonResponse({
        'success': False,
        'errors': errors,
    }, status=400)

# Usage in view
@require_http_methods(["POST"])
def submit_form(request):
    form = MyForm(request.POST)

    if form.is_valid():
        form.save()
        return JsonResponse({'success': True})
    else:
        return structured_error_response(form)
```

**JavaScript Error Handler:**
```javascript
function displayStructuredErrors(errors) {
    // Clear previous errors
    clearErrors();

    // Display field errors
    for (const [field, errorData] of Object.entries(errors.field_errors)) {
        const input = document.querySelector(`[name="${field}"]`);
        if (input) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback d-block';
            errorDiv.innerHTML = `<strong>${errorData.label}:</strong> ${errorData.messages.join(', ')}`;
            input.parentNode.appendChild(errorDiv);
            input.classList.add('is-invalid');
        }
    }

    // Display non-field errors
    if (errors.non_field_errors.length > 0) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger';
        alertDiv.innerHTML = errors.non_field_errors.map(err =>
            `<div>${err}</div>`
        ).join('');
        document.getElementById('form-container').prepend(alertDiv);
    }
}

function clearErrors() {
    document.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
    document.querySelectorAll('.is-invalid').forEach(el =>
        el.classList.remove('is-invalid')
    );
    document.querySelectorAll('.alert-danger').forEach(el => el.remove());
}
```

### Error Response with Field Focus

**JavaScript:**
```javascript
function displayErrorsAndFocus(errors) {
    let firstErrorField = null;

    for (const [field, messages] of Object.entries(errors)) {
        const input = document.querySelector(`[name="${field}"]`);
        if (input) {
            // Display error
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.textContent = messages.join(', ');
            input.parentNode.appendChild(errorDiv);
            input.classList.add('is-invalid');

            // Track first error field
            if (!firstErrorField) {
                firstErrorField = input;
            }
        }
    }

    // Focus first error field
    if (firstErrorField) {
        firstErrorField.focus();
        firstErrorField.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}
```

## htmx Integration

htmx enables AJAX with minimal JavaScript.

### Installation

```html
<!-- CDN -->
<script src="https://unpkg.com/htmx.org@1.9.10"></script>

<!-- Or via npm -->
npm install htmx.org
```

### Basic htmx Form

**Template:**
```django
<form hx-post="{% url 'contact_submit' %}"
      hx-target="#result"
      hx-swap="innerHTML"
      hx-indicator="#spinner">
    {% csrf_token %}

    {{ form.as_p }}

    <button type="submit">
        Submit
        <span id="spinner" class="htmx-indicator spinner-border spinner-border-sm"></span>
    </button>
</form>

<div id="result"></div>
```

**Django View:**
```python
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET", "POST"])
def contact_form(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'partials/success.html', {
                'message': 'Form submitted successfully!'
            })
        else:
            return render(request, 'partials/form.html', {
                'form': form
            }, status=400)
    else:
        form = ContactForm()
        return render(request, 'contact_form.html', {'form': form})
```

### htmx with Out-of-Band Swaps

Update multiple elements in one request.

**Template:**
```django
<form hx-post="{% url 'submit' %}" hx-target="#form-container">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Submit</button>
</form>

<div id="form-container"></div>
<div id="notifications"></div>
```

**Response Template (partials/response.html):**
```django
<!-- Main swap target -->
<div id="form-container">
    {% if form.errors %}
        {{ form.as_p }}
    {% else %}
        <p>Form submitted successfully!</p>
    {% endif %}
</div>

<!-- Out-of-band swap -->
<div id="notifications" hx-swap-oob="true">
    <div class="alert alert-success">
        Thank you for your submission!
    </div>
</div>
```

### htmx Form Validation

Real-time field validation.

**Template:**
```django
<form>
    {% csrf_token %}

    <div class="form-group">
        <label for="email">Email</label>
        <input type="email"
               name="email"
               hx-post="{% url 'validate_email' %}"
               hx-trigger="blur"
               hx-target="#email-error"
               hx-swap="innerHTML"
               class="form-control">
        <div id="email-error"></div>
    </div>

    <button type="submit">Submit</button>
</form>
```

**Django View:**
```python
@require_http_methods(["POST"])
def validate_email(request):
    email = request.POST.get('email')
    form = ContactForm({'email': email})

    if form.is_valid():
        return HttpResponse('<span class="text-success">✓ Valid email</span>')
    else:
        error = form.errors.get('email', [''])[0]
        return HttpResponse(
            f'<span class="text-danger">{error}</span>',
            status=400
        )
```

## Real-time Validation

### Pattern 1: Blur Event Validation

**JavaScript:**
```javascript
document.querySelectorAll('input, textarea, select').forEach(field => {
    field.addEventListener('blur', async (e) => {
        const fieldName = e.target.name;
        const fieldValue = e.target.value;

        // Skip if empty and not required
        if (!fieldValue && !e.target.required) return;

        try {
            const response = await fetch(`/api/validate/${fieldName}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
                body: JSON.stringify({ [fieldName]: fieldValue })
            });

            const data = await response.json();

            if (data.valid) {
                e.target.classList.remove('is-invalid');
                e.target.classList.add('is-valid');
            } else {
                e.target.classList.remove('is-valid');
                e.target.classList.add('is-invalid');
                showFieldError(e.target, data.error);
            }
        } catch (error) {
            console.error('Validation error:', error);
        }
    });
});
```

**Django View:**
```python
@require_http_methods(["POST"])
def validate_field(request, field_name):
    data = json.loads(request.body)
    form = ContactForm(data)

    # Validate specific field
    try:
        form.fields[field_name].clean(data.get(field_name))
        return JsonResponse({'valid': True})
    except ValidationError as e:
        return JsonResponse({
            'valid': False,
            'error': e.message
        }, status=400)
```

### Pattern 2: Debounced Input Validation

**JavaScript:**
```javascript
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

const validateField = debounce(async (field) => {
    const response = await fetch(`/api/validate/${field.name}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({ [field.name]: field.value })
    });

    const data = await response.json();
    updateFieldValidation(field, data);
}, 500);  // 500ms debounce

document.querySelectorAll('input').forEach(field => {
    field.addEventListener('input', () => validateField(field));
});
```

## File Upload via AJAX

### FormData File Upload

**HTML:**
```html
<form id="upload-form">
    {% csrf_token %}

    <input type="file" name="file" id="file-input" required>

    <div id="progress-container" style="display: none;">
        <progress id="progress-bar" value="0" max="100"></progress>
        <span id="progress-text">0%</span>
    </div>

    <button type="submit">Upload</button>
</form>

<div id="result"></div>
```

**JavaScript:**
```javascript
document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    progressContainer.style.display = 'block';

    try {
        const xhr = new XMLHttpRequest();

        // Track upload progress
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                progressBar.value = percentComplete;
                progressText.textContent = `${Math.round(percentComplete)}%`;
            }
        });

        // Handle response
        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                document.getElementById('result').innerHTML =
                    `<div class="alert alert-success">${data.message}</div>`;
                form.reset();
            } else {
                const data = JSON.parse(xhr.responseText);
                displayErrors(data.errors);
            }
            progressContainer.style.display = 'none';
        });

        xhr.open('POST', form.action);
        xhr.setRequestHeader('X-CSRFToken', csrftoken);
        xhr.send(formData);

    } catch (error) {
        console.error('Upload error:', error);
        progressContainer.style.display = 'none';
    }
});
```

**Django View:**
```python
from django.core.files.storage import default_storage
from django.views.decorators.http import require_http_methods

@require_http_methods(["POST"])
def upload_file(request):
    form = FileUploadForm(request.POST, request.FILES)

    if form.is_valid():
        uploaded_file = form.cleaned_data['file']

        # Save file
        filename = default_storage.save(
            f'uploads/{uploaded_file.name}',
            uploaded_file
        )

        return JsonResponse({
            'success': True,
            'message': 'File uploaded successfully!',
            'filename': filename,
            'size': uploaded_file.size,
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors,
        }, status=400)
```

### Multiple File Upload

**HTML:**
```html
<input type="file" name="files" id="file-input" multiple>
```

**JavaScript:**
```javascript
document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const fileInput = document.getElementById('file-input');
    const files = fileInput.files;

    for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append('file', files[i]);
        formData.append('csrfmiddlewaretoken', csrftoken);

        try {
            const response = await fetch('/upload/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                },
                body: formData
            });

            const data = await response.json();
            console.log(`Uploaded ${files[i].name}:`, data);
        } catch (error) {
            console.error(`Error uploading ${files[i].name}:`, error);
        }
    }
});
```

## Best Practices

1. **Always include CSRF token** for POST requests
2. **Handle network errors gracefully** with try-catch
3. **Provide user feedback** during submission (loading state)
4. **Clear previous errors** before displaying new ones
5. **Focus first error field** for better UX
6. **Use appropriate HTTP status codes** (200, 400, 500)
7. **Validate on both client and server** never trust client-side only
8. **Debounce real-time validation** to avoid excessive requests
9. **Show upload progress** for file uploads
10. **Consider accessibility** for dynamic content updates

## See Also

- **CSRF Protection:** Django CSRF documentation
- **File Uploads:** `/home/user/django/.claude/skills/django-forms/reference/file_uploads.md`
- **Error Handling:** `/home/user/django/.claude/skills/django-forms/reference/validation.md`
- **CSS Frameworks:** `/home/user/django/.claude/skills/django-forms/reference/css_frameworks.md`
