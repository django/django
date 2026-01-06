# Admin Permissions Reference

Complete guide to Django admin permissions, including model-level and object-level permissions.

## Table of Contents

1. [Model-Level Permissions](#model-level-permissions)
2. [Object-Level Permissions](#object-level-permissions)
3. [Custom Permissions](#custom-permissions)
4. [Field-Level Permissions](#field-level-permissions)
5. [Row-Level Security](#row-level-security)
6. [Advanced Patterns](#advanced-patterns)

## Model-Level Permissions

### Default Permission Methods

Django admin checks four permission methods for each model.

```python
from django.contrib import admin

class ArticleAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        """Can user add new objects?"""
        return request.user.has_perm('articles.add_article')

    def has_change_permission(self, request, obj=None):
        """Can user change objects?"""
        return request.user.has_perm('articles.change_article')

    def has_delete_permission(self, request, obj=None):
        """Can user delete objects?"""
        return request.user.has_perm('articles.delete_article')

    def has_view_permission(self, request, obj=None):
        """Can user view objects?"""
        return request.user.has_perm('articles.view_article')
```

### Deny All Add Permission

Prevent users from adding new objects.

```python
class LogEntryAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False  # Read-only model
```

### Role-Based Permissions

Limit access based on user groups.

```python
class ArticleAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        # Only editors and admins can change
        return (
            request.user.groups.filter(name__in=['Editors', 'Admins']).exists() or
            request.user.is_superuser
        )

    def has_delete_permission(self, request, obj=None):
        # Only admins can delete
        return (
            request.user.groups.filter(name='Admins').exists() or
            request.user.is_superuser
        )
```

### Staff-Only Access

Require staff status.

```python
class ConfigAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        """Show module in admin?"""
        return request.user.is_staff and request.user.is_superuser
```

## Object-Level Permissions

### Basic Object-Level Permissions

Check permissions for specific objects.

```python
class ArticleAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        # Model-level: Can user access changelist?
        if obj is None:
            return True

        # Object-level: Can user edit this specific article?
        return (
            obj.author == request.user or
            request.user.is_superuser
        )

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True

        # Only author or superuser can delete
        return (
            obj.author == request.user or
            request.user.is_superuser
        )
```

### Queryset Filtering

Hide objects user can't access.

```python
class ArticleAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        """Only show objects user can view"""
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        # Regular users only see their own articles
        return qs.filter(author=request.user)
```

### Combined Permissions

Both filter queryset AND check object permissions.

```python
class ArticleAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        """Filter what user can see"""
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        # Editors see all published + their drafts
        if request.user.groups.filter(name='Editors').exists():
            return qs.filter(
                Q(status='published') |
                Q(author=request.user)
            )

        # Authors see only their own
        return qs.filter(author=request.user)

    def has_change_permission(self, request, obj=None):
        """Check if user can edit specific object"""
        if not super().has_change_permission(request, obj):
            return False

        if obj is None:
            return True

        # Can edit if owner or editor
        return (
            obj.author == request.user or
            request.user.groups.filter(name='Editors').exists() or
            request.user.is_superuser
        )
```

### Status-Based Permissions

Permissions based on object state.

```python
class ArticleAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True

        # Published articles can only be edited by editors
        if obj.status == 'published':
            return (
                request.user.groups.filter(name='Editors').exists() or
                request.user.is_superuser
            )

        # Draft articles can be edited by author
        return obj.author == request.user or request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True

        # Can't delete published articles
        if obj.status == 'published':
            return request.user.is_superuser

        # Can delete own drafts
        return obj.author == request.user or request.user.is_superuser
```

### Team-Based Permissions

Permissions based on team membership.

```python
class ProjectAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        # Show projects where user is team member
        return qs.filter(team_members=request.user).distinct()

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True

        # Team members can edit
        return (
            obj.team_members.filter(id=request.user.id).exists() or
            request.user.is_superuser
        )

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True

        # Only project owner can delete
        return obj.owner == request.user or request.user.is_superuser
```

## Custom Permissions

### Define Custom Permissions

Add custom permissions to model.

```python
# models.py
class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()

    class Meta:
        permissions = [
            ('publish_article', 'Can publish articles'),
            ('feature_article', 'Can feature articles'),
            ('export_article', 'Can export articles'),
        ]
```

### Check Custom Permissions

```python
class ArticleAdmin(admin.ModelAdmin):
    def has_publish_permission(self, request):
        """Check custom publish permission"""
        return request.user.has_perm('articles.publish_article')

    def has_feature_permission(self, request):
        """Check custom feature permission"""
        return request.user.has_perm('articles.feature_article')

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))

        # Make published_at readonly if user can't publish
        if not self.has_publish_permission(request):
            fields.append('published_at')

        return fields
```

### Custom Permissions in Actions

```python
@admin.action(description="Publish selected articles", permissions=['publish'])
def publish_articles(modeladmin, request, queryset):
    queryset.update(status='published', published_at=timezone.now())

class ArticleAdmin(admin.ModelAdmin):
    actions = [publish_articles]

    def has_publish_permission(self, request):
        return request.user.has_perm('articles.publish_article')
```

## Field-Level Permissions

### Readonly Fields Based on Permissions

```python
class ArticleAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly based on permissions"""
        fields = list(super().get_readonly_fields(request, obj))

        # Non-superusers can't edit these
        if not request.user.is_superuser:
            fields.extend(['view_count', 'slug'])

        # Only publishers can edit published_at
        if not request.user.has_perm('articles.publish_article'):
            fields.append('published_at')

        # Published articles: only title editable
        if obj and obj.status == 'published':
            fields.extend(['content', 'author'])

        return fields
```

### Hide Fields Based on Permissions

```python
class ArticleAdmin(admin.ModelAdmin):
    def get_fieldsets(self, request, obj=None):
        """Show/hide entire fieldsets"""
        fieldsets = [
            ('Basic Info', {
                'fields': ['title', 'content', 'author'],
            }),
        ]

        # Only show publish options to publishers
        if request.user.has_perm('articles.publish_article'):
            fieldsets.append(
                ('Publishing', {
                    'fields': ['status', 'published_at', 'featured'],
                })
            )

        # Only show analytics to admins
        if request.user.is_superuser:
            fieldsets.append(
                ('Analytics', {
                    'fields': ['view_count', 'engagement_score'],
                    'classes': ['collapse'],
                })
            )

        return fieldsets

    def get_fields(self, request, obj=None):
        """Alternative: modify fields list"""
        fields = ['title', 'content', 'author']

        if request.user.has_perm('articles.publish_article'):
            fields.extend(['status', 'published_at'])

        return fields
```

### Conditional Field Visibility

```python
class ProductAdmin(admin.ModelAdmin):
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # Hide internal cost from non-admins
        if not request.user.is_superuser:
            if 'internal_cost' in form.base_fields:
                del form.base_fields['internal_cost']

        # Hide discount field from non-managers
        if not request.user.groups.filter(name='Managers').exists():
            if 'discount' in form.base_fields:
                form.base_fields['discount'].widget = forms.HiddenInput()

        return form
```

## Row-Level Security

### Filter by Organization

```python
class InvoiceAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        # Filter by user's organization
        try:
            org = request.user.profile.organization
            return qs.filter(organization=org)
        except:
            return qs.none()  # No access if no organization

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True

        if request.user.is_superuser:
            return True

        # Check same organization
        try:
            return obj.organization == request.user.profile.organization
        except:
            return False
```

### Multi-Tenant Filtering

```python
class TenantAdmin(admin.ModelAdmin):
    """Base admin for multi-tenant models"""

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        # Filter by tenant
        tenant = getattr(request.user, 'tenant', None)
        if tenant:
            return qs.filter(tenant=tenant)

        return qs.none()

    def save_model(self, request, obj, form, change):
        """Auto-assign tenant on create"""
        if not change and hasattr(request.user, 'tenant'):
            obj.tenant = request.user.tenant
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True

        if request.user.is_superuser:
            return True

        # Check same tenant
        if hasattr(obj, 'tenant') and hasattr(request.user, 'tenant'):
            return obj.tenant == request.user.tenant

        return False

class ProductAdmin(TenantAdmin):
    """Inherits tenant filtering"""
    list_display = ['name', 'price', 'tenant']
```

### Department-Based Access

```python
class EmployeeAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        # HR sees all employees
        if request.user.groups.filter(name='HR').exists():
            return qs

        # Managers see their department
        if hasattr(request.user, 'managed_department'):
            return qs.filter(department=request.user.managed_department)

        # Regular users see only themselves
        return qs.filter(user=request.user)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True

        if request.user.is_superuser:
            return True

        # HR can edit all
        if request.user.groups.filter(name='HR').exists():
            return True

        # Managers can edit their department
        if hasattr(request.user, 'managed_department'):
            return obj.department == request.user.managed_department

        # Users can edit only themselves
        return obj.user == request.user
```

## Advanced Patterns

### Dynamic Permission Checks

```python
class OrderAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False

        if obj is None:
            return True

        # Complex business logic
        if obj.is_locked():
            return request.user.is_superuser

        if obj.requires_approval():
            return request.user.groups.filter(name='Approvers').exists()

        if obj.is_high_value():
            return request.user.has_perm('orders.change_high_value_order')

        return True
```

### Time-Based Permissions

```python
from django.utils import timezone
from datetime import timedelta

class ArticleAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True

        if request.user.is_superuser:
            return True

        # Can't edit articles older than 30 days
        cutoff = timezone.now() - timedelta(days=30)
        if obj.created_at < cutoff:
            return False

        # Can edit own articles
        return obj.author == request.user

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))

        if obj:
            # Lock title after 7 days
            week_ago = timezone.now() - timedelta(days=7)
            if obj.created_at < week_ago:
                fields.append('title')

        return fields
```

### Hierarchical Permissions

```python
class CommentAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True

        if request.user.is_superuser:
            return True

        # Comment author can delete
        if obj.author == request.user:
            return True

        # Article author can delete comments on their article
        if obj.article.author == request.user:
            return True

        # Moderators can delete any comment
        if request.user.groups.filter(name='Moderators').exists():
            return True

        return False
```

### Permission Delegation

```python
class ProjectAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True

        if request.user.is_superuser:
            return True

        # Project owner
        if obj.owner == request.user:
            return True

        # Delegated editors
        if obj.editors.filter(id=request.user.id).exists():
            return True

        # Team members with edit permission
        membership = obj.team_memberships.filter(
            user=request.user,
            can_edit=True
        ).exists()

        return membership
```

### Approval Workflow Permissions

```python
class DocumentAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True

        if request.user.is_superuser:
            return True

        # Author can edit draft
        if obj.status == 'draft' and obj.author == request.user:
            return True

        # Reviewers can edit submitted documents
        if obj.status == 'submitted':
            return request.user.groups.filter(name='Reviewers').exists()

        # Approved documents can't be edited
        if obj.status == 'approved':
            return False

        return False

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))

        if obj:
            if obj.status == 'submitted':
                # Reviewers can only edit status and comments
                if request.user.groups.filter(name='Reviewers').exists():
                    fields.extend(['title', 'content', 'author'])

            if obj.status == 'approved':
                # Everything readonly when approved
                fields.extend(['title', 'content', 'status'])

        return fields
```

## Complete Examples

### Blog with Role-Based Permissions

```python
from django.contrib import admin
from django.db.models import Q

class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'status', 'published_at']
    list_filter = ['status', 'author']
    search_fields = ['title', 'content']

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        # Editors see all
        if request.user.groups.filter(name='Editors').exists():
            return qs

        # Authors see only their own
        return qs.filter(author=request.user)

    def has_add_permission(self, request):
        # Authors and above can add
        return (
            request.user.groups.filter(
                name__in=['Authors', 'Editors']
            ).exists() or
            request.user.is_superuser
        )

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False

        if obj is None:
            return True

        # Superusers can edit all
        if request.user.is_superuser:
            return True

        # Editors can edit all
        if request.user.groups.filter(name='Editors').exists():
            return True

        # Authors can edit own drafts
        if obj.author == request.user and obj.status == 'draft':
            return True

        return False

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True

        # Only superusers and editors can delete
        return (
            request.user.is_superuser or
            request.user.groups.filter(name='Editors').exists()
        )

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))

        if obj:
            # Published articles: content readonly for authors
            if obj.status == 'published':
                if not request.user.groups.filter(name='Editors').exists():
                    fields.extend(['title', 'content'])

            # Always readonly
            fields.extend(['created_at', 'updated_at'])

        return fields

    @admin.action(description="Publish selected articles", permissions=['publish'])
    def publish_articles(self, request, queryset):
        updated = queryset.filter(status='draft').update(
            status='published',
            published_at=timezone.now()
        )
        self.message_user(request, f"Published {updated} articles.")

    def has_publish_permission(self, request):
        return (
            request.user.groups.filter(name='Editors').exists() or
            request.user.is_superuser
        )

    actions = ['publish_articles']

admin.site.register(Article, ArticleAdmin)
```

### Multi-Tenant E-commerce

```python
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'price', 'store']
    list_filter = ['store', 'category']
    search_fields = ['name', 'sku']

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        # Filter by user's stores
        if hasattr(request.user, 'stores'):
            return qs.filter(store__in=request.user.stores.all())

        return qs.none()

    def has_add_permission(self, request):
        # Must have at least one store
        if request.user.is_superuser:
            return True

        return hasattr(request.user, 'stores') and request.user.stores.exists()

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False

        if obj is None:
            return True

        if request.user.is_superuser:
            return True

        # Check if product belongs to user's store
        if hasattr(request.user, 'stores'):
            return request.user.stores.filter(id=obj.store_id).exists()

        return False

    def has_delete_permission(self, request, obj=None):
        # Same as change permission
        return self.has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        # Auto-assign store on create
        if not change and not obj.store_id:
            if hasattr(request.user, 'stores'):
                obj.store = request.user.stores.first()

        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Limit store choices
        if db_field.name == 'store':
            if not request.user.is_superuser and hasattr(request.user, 'stores'):
                kwargs['queryset'] = request.user.stores.all()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(Product, ProductAdmin)
```

## Best Practices

1. **Always Check Superuser**: Include superuser checks in permission methods
2. **Filter Querysets**: Use `get_queryset()` to hide inaccessible objects
3. **Handle None**: Check `if obj is None` for model-level permissions
4. **Use Groups**: Prefer groups over individual permissions for roles
5. **Test Edge Cases**: Test with different user roles and object states
6. **Log Access**: Log permission denials for auditing
7. **Fail Secure**: Default to denying access when in doubt

## Troubleshooting

### User Can't See Any Objects

**Check**: `get_queryset()` might be filtering everything out.

**Solution**: Verify queryset logic and user attributes.

### Can't Edit Despite Permissions

**Check**: `has_change_permission()` might deny object-level access.

**Solution**: Add logging to see which check fails.

### Readonly Fields Not Working

**Check**: `get_readonly_fields()` might not include field.

**Solution**: Verify field name and method logic.

### Actions Not Showing

**Check**: Permission check method missing or denying access.

**Solution**: Implement `has_{permission}_permission()` method.
