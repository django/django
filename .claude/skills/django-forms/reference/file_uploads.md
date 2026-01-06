# File Upload Patterns Reference

Complete guide to handling file uploads securely in Django forms.

## Table of Contents

- [Basic File Upload](#basic-file-upload)
- [File Validation](#file-validation)
- [Security Considerations](#security-considerations)
- [Large File Handling](#large-file-handling)
- [Image Processing](#image-processing)
- [Multiple File Uploads](#multiple-file-uploads)

## Basic File Upload

### Simple File Upload Form

**Model:**
```python
# models.py
from django.db import models

class Document(models.Model):
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
```

**Form:**
```python
# forms.py
from django import forms
from .models import Document

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx',
            })
        }
```

**View:**
```python
# views.py
from django.shortcuts import render, redirect
from .forms import DocumentForm

def upload_document(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)  # Don't forget request.FILES!
        if form.is_valid():
            form.save()
            return redirect('document_list')
    else:
        form = DocumentForm()
    return render(request, 'upload.html', {'form': form})
```

**Template:**
```django
<form method="post" enctype="multipart/form-data">  <!-- Required enctype! -->
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Upload</button>
</form>
```

### Image Upload

**Model:**
```python
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/%d/',  # Organized by date
        blank=True,
        null=True
    )
    bio = models.TextField()
```

**Form:**
```python
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'bio']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control'
            })
        }
```

## File Validation

### File Size Validation

```python
from django import forms
from django.core.exceptions import ValidationError

def validate_file_size(file):
    """Limit file size to 5MB."""
    max_size_mb = 5
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(
            f'File size cannot exceed {max_size_mb}MB. '
            f'Current size: {file.size / (1024 * 1024):.2f}MB'
        )

class DocumentForm(forms.ModelForm):
    file = forms.FileField(
        validators=[validate_file_size]
    )

    class Meta:
        model = Document
        fields = ['title', 'file']
```

### File Extension Validation

```python
from django.core.validators import FileExtensionValidator

class DocumentForm(forms.ModelForm):
    file = forms.FileField(
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'txt'],
                message='Only PDF, DOC, DOCX, and TXT files are allowed.'
            )
        ]
    )

    class Meta:
        model = Document
        fields = ['title', 'file']
```

### MIME Type Validation

**Install python-magic:**
```bash
pip install python-magic
# On Windows:
pip install python-magic-bin
```

**Validator:**
```python
import magic
from django.core.exceptions import ValidationError

def validate_file_mime_type(file):
    """Verify actual MIME type matches extension."""
    # Allowed MIME types
    allowed_mime_types = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
    ]

    # Read file header to determine actual MIME type
    file_mime = magic.from_buffer(file.read(1024), mime=True)
    file.seek(0)  # Reset file pointer

    if file_mime not in allowed_mime_types:
        raise ValidationError(
            f'Invalid file type: {file_mime}. '
            f'Allowed types: PDF, DOC, DOCX, TXT'
        )

def validate_image_mime_type(file):
    """Verify file is actually an image."""
    valid_mime_types = [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp'
    ]

    file_mime = magic.from_buffer(file.read(1024), mime=True)
    file.seek(0)

    if file_mime not in valid_mime_types:
        raise ValidationError(
            f'Invalid image type: {file_mime}. '
            f'Allowed: JPEG, PNG, GIF, WebP'
        )
```

**Usage:**
```python
class DocumentForm(forms.ModelForm):
    file = forms.FileField(
        validators=[
            validate_file_size,
            FileExtensionValidator(['pdf', 'doc', 'docx']),
            validate_file_mime_type,
        ]
    )
```

### Combined Validation

```python
from django.utils.deconstruct import deconstructible

@deconstructible
class FileValidator:
    """Comprehensive file validator."""

    def __init__(self, max_size_mb=5, allowed_extensions=None, allowed_mimes=None):
        self.max_size_mb = max_size_mb
        self.allowed_extensions = allowed_extensions or []
        self.allowed_mimes = allowed_mimes or []

    def __call__(self, file):
        # Size validation
        if file.size > self.max_size_mb * 1024 * 1024:
            raise ValidationError(
                f'File size cannot exceed {self.max_size_mb}MB.'
            )

        # Extension validation
        if self.allowed_extensions:
            ext = file.name.split('.')[-1].lower()
            if ext not in self.allowed_extensions:
                raise ValidationError(
                    f'File extension ".{ext}" is not allowed. '
                    f'Allowed: {", ".join(self.allowed_extensions)}'
                )

        # MIME type validation
        if self.allowed_mimes:
            import magic
            file_mime = magic.from_buffer(file.read(1024), mime=True)
            file.seek(0)

            if file_mime not in self.allowed_mimes:
                raise ValidationError(
                    f'File type {file_mime} is not allowed.'
                )

# Usage
class DocumentForm(forms.ModelForm):
    file = forms.FileField(
        validators=[
            FileValidator(
                max_size_mb=5,
                allowed_extensions=['pdf', 'doc', 'docx'],
                allowed_mimes=[
                    'application/pdf',
                    'application/msword',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                ]
            )
        ]
    )
```

## Security Considerations

### 1. Validate MIME Type AND Extension

**Why:** Users can rename `malware.exe` to `document.pdf`. Always verify actual file type.

```python
def validate_document_security(file):
    """Security-focused document validation."""
    # Check extension
    ext = file.name.split('.')[-1].lower()
    if ext not in ['pdf', 'doc', 'docx']:
        raise ValidationError('Invalid file extension.')

    # Verify actual MIME type
    import magic
    file_mime = magic.from_buffer(file.read(1024), mime=True)
    file.seek(0)

    allowed_mimes = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }

    if file_mime != allowed_mimes.get(ext):
        raise ValidationError(
            f'File extension ".{ext}" does not match file content type.'
        )
```

### 2. Sanitize Filenames

```python
import os
import re
from django.utils.text import get_valid_filename

def sanitize_filename(filename):
    """Remove dangerous characters from filename."""
    # Remove path components
    filename = os.path.basename(filename)

    # Django's built-in sanitization
    filename = get_valid_filename(filename)

    # Additional sanitization
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)

    return filename

# In form
def clean_file(self):
    file = self.cleaned_data.get('file')
    if file:
        file.name = sanitize_filename(file.name)
    return file
```

### 3. Randomize Upload Filenames

```python
import uuid
from django.utils.text import slugify

def upload_to_random(instance, filename):
    """Generate random filename while preserving extension."""
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4()}.{ext}'
    return f'uploads/{filename}'

class Document(models.Model):
    file = models.FileField(upload_to=upload_to_random)
```

### 4. Store Outside Web Root (Recommended)

```python
# settings.py
MEDIA_ROOT = '/var/app/secure_uploads/'  # Outside web root
MEDIA_URL = '/media/'

# urls.py (development only!)
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Production:** Serve files through a view that checks permissions:

```python
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required
import os

@login_required
def serve_protected_file(request, file_id):
    """Serve file only to authorized users."""
    document = get_object_or_404(Document, id=file_id)

    # Check permissions
    if document.user != request.user and not request.user.is_staff:
        raise Http404

    # Serve file
    file_path = document.file.path
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{document.file.name}"'
        return response
    else:
        raise Http404
```

### 5. Scan for Malware (Production)

**Using ClamAV:**
```bash
pip install pyclamd
```

```python
import pyclamd

def scan_file_for_viruses(file):
    """Scan uploaded file for viruses."""
    try:
        cd = pyclamd.ClamdUnixSocket()
        # Scan file content
        scan_result = cd.scan_stream(file.read())
        file.seek(0)

        if scan_result:
            raise ValidationError('File failed virus scan.')
    except Exception as e:
        # Log error, don't block upload
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Virus scan failed: {e}')

class DocumentForm(forms.ModelForm):
    file = forms.FileField(
        validators=[scan_file_for_viruses]
    )
```

## Large File Handling

### Chunked Upload

**For files >10MB, use chunked uploads.**

**JavaScript:**
```javascript
async function uploadLargeFile(file, uploadUrl) {
    const chunkSize = 1024 * 1024; // 1MB chunks
    const chunks = Math.ceil(file.size / chunkSize);

    for (let i = 0; i < chunks; i++) {
        const start = i * chunkSize;
        const end = Math.min(start + chunkSize, file.size);
        const chunk = file.slice(start, end);

        const formData = new FormData();
        formData.append('file', chunk);
        formData.append('chunk', i);
        formData.append('chunks', chunks);
        formData.append('filename', file.name);

        const response = await fetch(uploadUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        // Update progress
        const progress = ((i + 1) / chunks) * 100;
        updateProgress(progress);
    }
}
```

**Django View:**
```python
import os
from django.conf import settings
from django.views.decorators.http import require_http_methods

@require_http_methods(["POST"])
def chunked_upload(request):
    chunk = request.FILES.get('file')
    chunk_number = int(request.POST.get('chunk'))
    total_chunks = int(request.POST.get('chunks'))
    filename = request.POST.get('filename')

    # Create temp directory
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
    os.makedirs(temp_dir, exist_ok=True)

    # Save chunk
    chunk_path = os.path.join(temp_dir, f'{filename}.part{chunk_number}')
    with open(chunk_path, 'wb') as f:
        for chunk_data in chunk.chunks():
            f.write(chunk_data)

    # If last chunk, combine all chunks
    if chunk_number == total_chunks - 1:
        final_path = os.path.join(settings.MEDIA_ROOT, 'uploads', filename)
        os.makedirs(os.path.dirname(final_path), exist_ok=True)

        with open(final_path, 'wb') as final_file:
            for i in range(total_chunks):
                chunk_path = os.path.join(temp_dir, f'{filename}.part{i}')
                with open(chunk_path, 'rb') as chunk_file:
                    final_file.write(chunk_file.read())
                os.remove(chunk_path)  # Clean up

        return JsonResponse({'success': True, 'file_path': final_path})

    return JsonResponse({'success': True, 'chunk': chunk_number})
```

### Memory-Efficient Processing

```python
from django.core.files.uploadedfile import UploadedFile

def process_large_file(uploaded_file: UploadedFile):
    """Process file in chunks to avoid memory issues."""
    chunk_size = 8192  # 8KB chunks

    for chunk in uploaded_file.chunks(chunk_size):
        # Process chunk
        process_data(chunk)

# Example: Calculate hash without loading entire file
import hashlib

def calculate_file_hash(file):
    """Calculate SHA256 hash of uploaded file."""
    sha256 = hashlib.sha256()

    for chunk in file.chunks():
        sha256.update(chunk)

    file.seek(0)  # Reset file pointer
    return sha256.hexdigest()
```

### Upload Progress Tracking

**Using Session:**
```python
from django.core.cache import cache

class UploadProgressMiddleware:
    """Track upload progress."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST' and request.META.get('HTTP_X_PROGRESS_ID'):
            progress_id = request.META['HTTP_X_PROGRESS_ID']

            # Store progress in cache
            def progress_callback(current, total):
                cache.set(
                    f'upload_progress_{progress_id}',
                    {'current': current, 'total': total},
                    timeout=60
                )

            # This would require custom upload handler
            # See Django's UploadFileException

        response = self.get_response(request)
        return response

# View to check progress
def upload_progress(request, progress_id):
    progress = cache.get(f'upload_progress_{progress_id}', {})
    return JsonResponse(progress)
```

## Image Processing

### Resize Images on Upload

```bash
pip install Pillow
```

```python
from PIL import Image
from django.core.files.base import ContentFile
from io import BytesIO

def resize_image(image_field, max_width=800, max_height=800):
    """Resize image while maintaining aspect ratio."""
    img = Image.open(image_field)

    # Convert RGBA to RGB if necessary
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')

    # Calculate new dimensions
    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    # Save to BytesIO
    output = BytesIO()
    img.save(output, format='JPEG', quality=85)
    output.seek(0)

    return ContentFile(output.read())

# In form
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar']

    def save(self, commit=True):
        instance = super().save(commit=False)

        if instance.avatar:
            # Resize avatar
            resized = resize_image(instance.avatar)
            instance.avatar.save(
                instance.avatar.name,
                resized,
                save=False
            )

        if commit:
            instance.save()

        return instance
```

### Create Thumbnails

```python
from django.db import models
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

class Photo(models.Model):
    image = models.ImageField(upload_to='photos/')
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True)

    def save(self, *args, **kwargs):
        if self.image:
            # Create thumbnail
            img = Image.open(self.image)
            img.thumbnail((200, 200), Image.Resampling.LANCZOS)

            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            # Save thumbnail
            thumb_io = BytesIO()
            img.save(thumb_io, format='JPEG', quality=85)
            thumb_io.seek(0)

            self.thumbnail.save(
                f'thumb_{self.image.name}',
                InMemoryUploadedFile(
                    thumb_io, None, f'thumb_{self.image.name}',
                    'image/jpeg', thumb_io.getbuffer().nbytes, None
                ),
                save=False
            )

        super().save(*args, **kwargs)
```

### Validate Image Dimensions

```python
from PIL import Image

def validate_image_dimensions(image):
    """Ensure image is at least 800x600 pixels."""
    img = Image.open(image)
    min_width, min_height = 800, 600

    if img.width < min_width or img.height < min_height:
        raise ValidationError(
            f'Image must be at least {min_width}x{min_height} pixels. '
            f'Uploaded: {img.width}x{img.height}'
        )

    image.seek(0)  # Reset file pointer
```

## Multiple File Uploads

### Multiple Files in Single Field

**Template:**
```html
<form method="post" enctype="multipart/form-data">
    {% csrf_token %}

    <input type="file" name="files" multiple class="form-control">

    <button type="submit">Upload</button>
</form>
```

**View:**
```python
def upload_multiple_files(request):
    if request.method == 'POST':
        files = request.FILES.getlist('files')

        for file in files:
            # Validate each file
            if file.size > 5 * 1024 * 1024:  # 5MB
                continue  # Skip or show error

            # Save file
            Document.objects.create(
                title=file.name,
                file=file
            )

        return redirect('success')

    return render(request, 'upload_multiple.html')
```

### Formset for Multiple Files

```python
from django.forms import modelformset_factory

# Create formset
DocumentFormSet = modelformset_factory(
    Document,
    fields=['title', 'file'],
    extra=3,  # Number of empty forms
    can_delete=True
)

# View
def upload_documents(request):
    if request.method == 'POST':
        formset = DocumentFormSet(request.POST, request.FILES)
        if formset.is_valid():
            formset.save()
            return redirect('document_list')
    else:
        formset = DocumentFormSet(queryset=Document.objects.none())

    return render(request, 'upload_formset.html', {'formset': formset})
```

**Template:**
```django
<form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    {{ formset.management_form }}

    {% for form in formset %}
        <div class="form-row">
            {{ form.as_p }}
        </div>
    {% endfor %}

    <button type="submit">Upload All</button>
</form>
```

## Best Practices

1. **Always validate file type** - Check extension AND MIME type
2. **Limit file size** - Prevent DOS attacks
3. **Sanitize filenames** - Remove dangerous characters
4. **Store files securely** - Outside web root or with permission checks
5. **Use unique filenames** - Prevent overwrites (UUID or hash)
6. **Scan for malware** - In production environments
7. **Process asynchronously** - For large files or heavy processing
8. **Clean up failed uploads** - Remove orphaned files
9. **Set appropriate permissions** - Read-only for uploaded files
10. **Monitor storage usage** - Implement quotas if necessary

## Configuration

```python
# settings.py

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Allowed file extensions (custom setting)
ALLOWED_UPLOAD_EXTENSIONS = ['pdf', 'doc', 'docx', 'jpg', 'png']

# Max file size (custom setting)
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
```

## See Also

- **Validation:** `/home/user/django/.claude/skills/django-forms/reference/validation.md`
- **AJAX Uploads:** `/home/user/django/.claude/skills/django-forms/reference/ajax_patterns.md`
- **Field Types:** `/home/user/django/.claude/skills/django-forms/reference/field_types.md`
