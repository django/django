# Django Skills Index

A searchable directory of Django Claude Skills organized by task, component, and workflow.

## Quick Reference Table

| Skill | Phase | Priority | Primary Use Cases | Dependencies |
|-------|-------|----------|-------------------|--------------|
| django-models | 1 | HIGH | Data modeling, ORM, migrations | - |
| django-testing | 1 | HIGH | Unit tests, integration tests, CI/CD | - |
| django-forms | 1 | HIGH | Form creation, validation, widgets | django-models |
| django-admin | 2 | HIGH | Admin customization, permissions | django-models |
| django-views | 2 | HIGH | Request handling, FBV/CBV, APIs | django-forms, django-models |
| django-templates | 2 | HIGH | Template rendering, filters, tags | django-views |
| django-signals | 3 | MEDIUM | Decoupled event handling | django-models |
| django-commands | 3 | MEDIUM | Management commands, automation | django-models |
| django-caching | 3 | MEDIUM | Performance optimization | django-views |
| django-settings | 4 | MEDIUM | Configuration management | - |
| django-middleware | 4 | LOW | Request/response processing | django-views |
| django-urls | 4 | LOW | URL routing, namespacing | django-views |

## Find Skills by Task

### "I need to..."

#### Data & Models
- **Create a new model** → [django-models](skills/django-models/SKILL.md)
- **Add a field to existing model** → [django-models](skills/django-models/SKILL.md) (workflow: add-field-migration)
- **Create model relationships** → [django-models](skills/django-models/SKILL.md) (reference: relationships.md)
- **Write complex queries** → [django-models](skills/django-models/SKILL.md) (reference: expressions.md, lookups.md)
- **Debug slow queries** → [django-models](skills/django-models/SKILL.md) (scripts: analyze_n_plus_one.py)
- **Use async ORM** → [django-models](skills/django-models/SKILL.md) (reference: async_orm_patterns.md)
- **Handle migrations** → [django-models](skills/django-models/SKILL.md) (workflows: migration-conflicts)
- **Validate data integrity** → [django-models](skills/django-models/SKILL.md) + [validators](skills/_shared/validators.py)

#### Forms & Validation
- **Create a form** → [django-forms](skills/django-forms/SKILL.md)
- **Add custom validation** → [django-forms](skills/django-forms/SKILL.md) (reference: cross_field_validation.md)
- **Handle file uploads** → [django-forms](skills/django-forms/SKILL.md) (reference: file_upload_patterns.md)
- **Create multi-step forms** → [django-forms](skills/django-forms/SKILL.md) (workflows: form-wizards)
- **Integrate with frontend frameworks** → [django-forms](skills/django-forms/SKILL.md) (reference: css_framework_integration.md)
- **Make forms accessible** → [django-forms](skills/django-forms/SKILL.md) (reference: accessibility_checklist.md)
- **Validate files for security** → [django-forms](skills/django-forms/SKILL.md) (reference: file_upload_patterns.md)

#### Views & URLs
- **Create a view** → [django-views](skills/django-views/SKILL.md)
- **Choose FBV vs CBV** → [django-views](skills/django-views/SKILL.md) (reference: decision-matrix.md)
- **Build REST API without DRF** → [django-views](skills/django-views/SKILL.md) (reference: api_patterns.md)
- **Handle file downloads** → [django-views](skills/django-views/SKILL.md) (reference: file_handling.md)
- **Implement pagination** → [django-views](skills/django-views/SKILL.md) (reference: pagination.md)
- **Use async views** → [django-views](skills/django-views/SKILL.md) (reference: async_views.md)
- **Add rate limiting** → [django-views](skills/django-views/SKILL.md) (reference: rate_limiting.md)
- **Configure URL routing** → [django-urls](skills/django-urls/SKILL.md)

#### Templates
- **Create template** → [django-templates](skills/django-templates/SKILL.md)
- **Build custom template tags** → [django-templates](skills/django-templates/SKILL.md)
- **Create custom filters** → [django-templates](skills/django-templates/SKILL.md)
- **Optimize template rendering** → [django-templates](skills/django-templates/SKILL.md) + [django-caching](skills/django-caching/SKILL.md)
- **Implement template inheritance** → [django-templates](skills/django-templates/SKILL.md)

#### Admin Interface
- **Customize admin** → [django-admin](skills/django-admin/SKILL.md)
- **Add custom admin views** → [django-admin](skills/django-admin/SKILL.md) (reference: custom_views.md)
- **Configure admin permissions** → [django-admin](skills/django-admin/SKILL.md) (reference: permissions_matrix.md)
- **Optimize admin queries** → [django-admin](skills/django-admin/SKILL.md) (reference: query_optimization.md)
- **Create custom admin actions** → [django-admin](skills/django-admin/SKILL.md) (workflows: admin-actions)
- **Add admin audit trails** → [django-admin](skills/django-admin/SKILL.md) (reference: logging.md)
- **Use admin autocomplete** → [django-admin](skills/django-admin/SKILL.md) (reference: autocomplete.md)

#### Testing & Quality
- **Write unit tests** → [django-testing](skills/django-testing/SKILL.md)
- **Test async code** → [django-testing](skills/django-testing/SKILL.md) (reference: async_testing.md)
- **Mock external services** → [django-testing](skills/django-testing/SKILL.md) (reference: mocking.md)
- **Set up CI/CD** → [django-testing](skills/django-testing/SKILL.md) (reference: ci_cd_pipelines.md)
- **Run parallel tests** → [django-testing](skills/django-testing/SKILL.md) (reference: parallel_testing.md)
- **Measure test coverage** → [django-testing](skills/django-testing/SKILL.md) (reference: coverage.md)
- **Debug flaky tests** → [django-testing](skills/django-testing/SKILL.md) (scripts: flaky_test_detector.py)

#### Performance
- **Add caching** → [django-caching](skills/django-caching/SKILL.md)
- **Optimize queries** → [django-models](skills/django-models/SKILL.md) (scripts: analyze_n_plus_one.py)
- **Cache views** → [django-views](skills/django-views/SKILL.md) + [django-caching](skills/django-caching/SKILL.md)
- **Cache templates** → [django-templates](skills/django-templates/SKILL.md) + [django-caching](skills/django-caching/SKILL.md)
- **Profile performance** → [django-testing](skills/django-testing/SKILL.md) (scripts: performance_baseline.py)

#### Background Tasks & Commands
- **Create management command** → [django-commands](skills/django-commands/SKILL.md)
- **Build data import command** → [django-commands](skills/django-commands/SKILL.md) (scripts: generate_import_command.py)
- **Add progress reporting** → [django-commands](skills/django-commands/SKILL.md) (reference: progress_reporting.md)
- **Use async in commands** → [django-commands](skills/django-commands/SKILL.md) (reference: async_commands.md)
- **Handle large datasets** → [django-commands](skills/django-commands/SKILL.md) (reference: memory_efficiency.md)

#### Event Handling
- **Create signals** → [django-signals](skills/django-signals/SKILL.md)
- **Debug signal chains** → [django-signals](skills/django-signals/SKILL.md) (scripts: map_signal_dependencies.py)
- **Handle signal anti-patterns** → [django-signals](skills/django-signals/SKILL.md) (reference: anti-patterns.md)

#### Configuration
- **Manage settings** → [django-settings](skills/django-settings/SKILL.md)
- **Configure environments** → [django-settings](skills/django-settings/SKILL.md)
- **Handle secrets** → [django-settings](skills/django-settings/SKILL.md)

#### Request Processing
- **Create middleware** → [django-middleware](skills/django-middleware/SKILL.md)
- **Process requests globally** → [django-middleware](skills/django-middleware/SKILL.md)
- **Add response headers** → [django-middleware](skills/django-middleware/SKILL.md)

## Find Skills by Django Component

### Models (`django.db.models`)
**Primary Skill**: [django-models](skills/django-models/SKILL.md)

**Key Workflows**:
- Model creation and fields
- Relationships (ForeignKey, ManyToMany, OneToOne)
- Migrations and schema changes
- QuerySet API and ORM operations
- Async ORM (Django 4.1+)
- Custom managers and querysets
- Model validation and constraints

**Related Skills**:
- [django-admin](skills/django-admin/SKILL.md) - Admin model registration
- [django-forms](skills/django-forms/SKILL.md) - ModelForm creation
- [django-signals](skills/django-signals/SKILL.md) - Model signals
- [validators](skills/_shared/validators.py) - Model validation

**Reference Files**:
- `async_orm_patterns.md` - Async database operations
- `expressions.md` - F, Q, Case, Window, Subquery
- `lookups.md` - Field lookups and custom lookups
- `constraints.md` - Database constraints
- `relationships.md` - Model relationships
- `inheritance_guide.md` - Model inheritance patterns

### Forms (`django.forms`)
**Primary Skill**: [django-forms](skills/django-forms/SKILL.md)

**Key Workflows**:
- Form and ModelForm creation
- Field validation (single and cross-field)
- Widget customization
- File upload handling
- Form rendering and templates
- Multi-step form wizards

**Related Skills**:
- [django-models](skills/django-models/SKILL.md) - ModelForm source
- [django-views](skills/django-views/SKILL.md) - Form processing in views
- [django-templates](skills/django-templates/SKILL.md) - Form rendering
- [validators](skills/_shared/validators.py) - Form validation

**Reference Files**:
- `cross_field_validation.md` - Multi-field validation
- `file_upload_patterns.md` - Secure file handling
- `css_framework_integration.md` - Bootstrap/Tailwind
- `accessibility_checklist.md` - WCAG compliance
- `javascript_integration.md` - Client-side patterns

### Views (`django.views`)
**Primary Skill**: [django-views](skills/django-views/SKILL.md)

**Key Workflows**:
- Function-based views (FBV)
- Class-based views (CBV)
- Generic views customization
- Async views
- API responses (JsonResponse)
- File uploads/downloads

**Related Skills**:
- [django-forms](skills/django-forms/SKILL.md) - Form handling
- [django-templates](skills/django-templates/SKILL.md) - Template rendering
- [django-urls](skills/django-urls/SKILL.md) - URL configuration
- [django-caching](skills/django-caching/SKILL.md) - View caching

**Reference Files**:
- `async_views.md` - Async view patterns
- `api_patterns.md` - REST without DRF
- `mixin_composition.md` - CBV mixin usage
- `pagination.md` - Pagination patterns
- `rate_limiting.md` - Rate limiting strategies

### Templates (`django.template`)
**Primary Skill**: [django-templates](skills/django-templates/SKILL.md)

**Key Workflows**:
- Template creation and inheritance
- Custom template tags
- Custom filters
- Template optimization
- Context processors

**Related Skills**:
- [django-views](skills/django-views/SKILL.md) - Template context
- [django-forms](skills/django-forms/SKILL.md) - Form rendering
- [django-caching](skills/django-caching/SKILL.md) - Template caching

### Admin (`django.contrib.admin`)
**Primary Skill**: [django-admin](skills/django-admin/SKILL.md)

**Key Workflows**:
- ModelAdmin customization
- Inline configurations
- Admin actions
- Custom admin views
- Permissions and security
- Search and filtering

**Related Skills**:
- [django-models](skills/django-models/SKILL.md) - Model registration
- [django-forms](skills/django-forms/SKILL.md) - Admin forms

**Reference Files**:
- `permissions_matrix.md` - Permission patterns
- `custom_views.md` - Custom admin views
- `autocomplete.md` - Autocomplete widgets
- `facets.md` - Django 6.0+ faceting
- `widgets.md` - Admin widget types

### Testing (`django.test`)
**Primary Skill**: [django-testing](skills/django-testing/SKILL.md)

**Key Workflows**:
- Test case creation
- Fixtures and factories
- Async testing
- Integration testing
- CI/CD pipelines
- Coverage reporting

**Related Skills**:
- All skills (testing is cross-cutting)

**Reference Files**:
- `test_classes.md` - Test class hierarchy
- `async_testing.md` - Async test patterns
- `ci_cd_pipelines.md` - GitHub Actions, etc.
- `mocking.md` - Mock strategies
- `parallel_testing.md` - Parallel execution

### Management Commands (`django.core.management`)
**Primary Skill**: [django-commands](skills/django-commands/SKILL.md)

**Key Workflows**:
- Custom command creation
- Argument parsing
- Progress reporting
- Async commands
- Database operations in commands

**Related Skills**:
- [django-models](skills/django-models/SKILL.md) - Database access
- [django-testing](skills/django-testing/SKILL.md) - Command testing

**Reference Files**:
- `async_commands.md` - Async command patterns
- `progress_reporting.md` - Progress bars and logging
- `memory_efficiency.md` - Large dataset handling
- `interactive_patterns.md` - User interaction

### Signals (`django.dispatch`)
**Primary Skill**: [django-signals](skills/django-signals/SKILL.md)

**Key Workflows**:
- Signal creation
- Signal handlers
- Debugging signal chains
- Avoiding signal pitfalls

**Related Skills**:
- [django-models](skills/django-models/SKILL.md) - Model signals

### Caching (`django.core.cache`)
**Primary Skill**: [django-caching](skills/django-caching/SKILL.md)

**Key Workflows**:
- Cache configuration
- View caching
- Template caching
- Low-level cache API
- Cache invalidation

**Related Skills**:
- [django-views](skills/django-views/SKILL.md) - View caching
- [django-templates](skills/django-templates/SKILL.md) - Template caching

### Settings (`django.conf`)
**Primary Skill**: [django-settings](skills/django-settings/SKILL.md)

**Key Workflows**:
- Settings organization
- Environment-specific configuration
- Secret management
- Custom settings

### Middleware (`django.middleware`)
**Primary Skill**: [django-middleware](skills/django-middleware/SKILL.md)

**Key Workflows**:
- Custom middleware creation
- Request/response processing
- Middleware ordering

**Related Skills**:
- [django-views](skills/django-views/SKILL.md) - Request handling

### URLs (`django.urls`)
**Primary Skill**: [django-urls](skills/django-urls/SKILL.md)

**Key Workflows**:
- URL pattern configuration
- URL namespacing
- URL reversal
- Path converters

**Related Skills**:
- [django-views](skills/django-views/SKILL.md) - View mapping

## Skill Dependencies

### No Dependencies
- django-models
- django-settings
- django-testing (foundational)

### Depends on Models
- django-forms (ModelForm)
- django-admin (ModelAdmin)
- django-signals (model signals)
- django-commands (database operations)

### Depends on Forms
- django-views (form processing)
- django-admin (custom forms)

### Depends on Views
- django-templates (context)
- django-urls (view mapping)
- django-middleware (request processing)
- django-caching (view caching)

### Cross-Cutting
- django-testing (tests all components)
- django-caching (caches multiple layers)

## Skill Maturity Levels

### Phase 1: Foundation (Released)
Skills are comprehensive, tested, and production-ready:
- **django-models** - 80% coverage of Django ORM
- **django-testing** - 85% coverage of Django test framework
- **django-forms** - 85% coverage of Django forms

### Phase 2: Core Features (In Development)
Skills are being enhanced with advanced patterns:
- **django-admin** - Target: 90% coverage
- **django-views** - Target: 80% coverage
- **django-templates** - Target: 85% coverage

### Phase 3: Infrastructure (Planned)
Skills will cover specialized topics:
- **django-signals** - Target: 75% coverage
- **django-commands** - Target: 90% coverage
- **django-caching** - Target: 80% coverage

### Phase 4: Advanced (Future)
Skills for advanced configuration and customization:
- **django-settings** - Target: 85% coverage
- **django-middleware** - Target: 75% coverage
- **django-urls** - Target: 70% coverage

## Shared Utilities

### Django Analyzer
**Location**: `skills/_shared/django_analyzer.py`

**Use When**:
- Starting work on an existing project
- Generating skill-specific recommendations
- Detecting project patterns and conventions

**Provides**:
- Installed apps list
- Model inventory
- View detection (FBV/CBV)
- Form detection
- Database configuration
- Async pattern detection

**Example**:
```bash
python .claude/skills/_shared/django_analyzer.py /path/to/project
```

### Code Generator
**Location**: `skills/_shared/code_generator.py`

**Use When**:
- Generating Django boilerplate
- Creating code from templates
- Ensuring consistent formatting

**Provides**:
- Jinja2 template rendering
- Import management
- Django code formatting
- PEP 8 compliance

**Example**:
```python
from skills._shared.code_generator import DjangoCodeGenerator
generator = DjangoCodeGenerator()
code = generator.render_model_template(context)
```

### Validators
**Location**: `skills/_shared/validators.py`

**Use When**:
- Validating generated code
- Checking Django conventions
- Running pre-commit checks

**Provides**:
- Model validation
- Form validation
- URL pattern validation
- Migration validation
- Django system check integration

**Example**:
```python
from skills._shared.validators import validate_model_definition
errors = validate_model_definition(model_code)
```

## Finding Help

### By Error Message
- **"Model doesn't define a Meta.ordering"** → django-models (reference: best-practices.md)
- **"Form validation failed"** → django-forms (reference: validation.md)
- **"Reverse for 'name' not found"** → django-urls
- **"N+1 query detected"** → django-models (scripts: analyze_n_plus_one.py)
- **"Migration conflict"** → django-models (workflows: migration-conflicts)
- **"Test database setup failed"** → django-testing (reference: database_testing.md)

### By Django Version
- **Django 5.0+** → All skills are compatible
- **Django 4.2** → Check skill's version notes
- **Django 4.1** → Limited async support
- **Django 3.2** → Check compatibility matrix

### By Use Case
- **Blog/CMS** → Start with django-models, django-admin
- **REST API** → Start with django-views, django-models
- **Form-heavy app** → Start with django-forms, django-models
- **Background processing** → Start with django-commands, django-signals
- **High-traffic site** → Add django-caching early

## Next Steps

1. **Browse available skills**: Check the Quick Reference Table
2. **Read skill documentation**: Each skill has comprehensive docs
3. **Try the shared utilities**: Run django_analyzer on your project
4. **Follow workflows**: Start with Quick Start sections
5. **Contribute improvements**: See SKILLS_IMPROVEMENT_PLAN.md
