# Django Claude Skills Plan

## Executive Summary

This document outlines the plan for creating Claude Skills to help developers use Django more efficiently and idiomatically. Based on comprehensive codebase analysis, we've identified **8 primary skill areas** that address the most common pain points and automation opportunities.

---

## Identified Skill Areas

### 1. Django Models & ORM Skill (HIGH PRIORITY)
**Purpose:** Help with model design, query optimization, and migrations

**Pain Points Addressed:**
- N+1 query detection and resolution
- Complex prefetch_related/select_related optimization
- Migration conflicts and dependency issues
- Expression complexity (Q/F objects)
- Deletion cascade edge cases

**Key Features:**
- Generate model definitions from requirements
- Analyze and optimize querysets
- Detect N+1 queries and suggest fixes
- Create/debug migrations
- Generate model relationships

**Reference Files:**
- `django/db/models/base.py` - Model core
- `django/db/models/query.py` - QuerySet
- `django/db/models/fields/` - Field types
- `django/db/migrations/` - Migration system

---

### 2. Django Admin Skill (HIGH PRIORITY)
**Purpose:** Automate admin customization and configuration

**Pain Points Addressed:**
- Manual ModelAdmin boilerplate
- Optimal list_display/list_filter selection
- Inline configuration complexity
- Custom action/filter creation

**Key Features:**
- Generate ModelAdmin from model analysis
- Create custom filters and actions
- Configure inline relationships
- Optimize admin querysets
- Generate admin templates

**Reference Files:**
- `django/contrib/admin/options.py` - ModelAdmin core
- `django/contrib/admin/filters.py` - Filter system
- `django/contrib/admin/sites.py` - AdminSite

---

### 3. Django Forms Skill (HIGH PRIORITY)
**Purpose:** Automate form creation and validation

**Pain Points Addressed:**
- Form field boilerplate from models
- Custom validation logic
- Formset configuration
- Widget customization

**Key Features:**
- Generate forms from models/schemas
- Create validation patterns
- Build custom widgets
- Generate formsets for relationships
- Create form tests

**Reference Files:**
- `django/forms/forms.py` - Form classes
- `django/forms/fields.py` - Field types
- `django/forms/models.py` - ModelForm
- `django/forms/formsets.py` - Formsets

---

### 4. Django Views & URLs Skill (MEDIUM PRIORITY)
**Purpose:** Help with view patterns and URL routing

**Pain Points Addressed:**
- CBV mixin selection complexity
- URL pattern configuration
- Middleware creation
- Async/sync conversion

**Key Features:**
- Generate CBV from requirements
- Create URL configurations
- Build custom middleware
- Convert regex to path() syntax
- Generate view decorators

**Reference Files:**
- `django/views/generic/` - Generic views
- `django/urls/resolvers.py` - URL routing
- `django/middleware/` - Middleware

---

### 5. Django Testing Skill (MEDIUM PRIORITY)
**Purpose:** Automate test creation and optimization

**Pain Points Addressed:**
- Test boilerplate creation
- Query count assertions
- Fixture management
- Test performance issues

**Key Features:**
- Generate test cases from models/views
- Create assertion patterns
- Build fixtures from data
- Optimize test performance
- Generate factory classes

**Reference Files:**
- `django/test/testcases.py` - Test classes
- `django/test/client.py` - Test client
- `django/test/utils.py` - Test utilities

---

### 6. Django Management Commands Skill (MEDIUM PRIORITY)
**Purpose:** Help create custom management commands

**Pain Points Addressed:**
- Command boilerplate
- Argument parsing complexity
- Error handling patterns
- Command composition

**Key Features:**
- Generate command scaffolds
- Create argument configurations
- Build command compositions
- Generate command tests
- Add proper output styling

**Reference Files:**
- `django/core/management/base.py` - BaseCommand
- `django/core/management/commands/` - Built-in commands

---

### 7. Django Settings & Configuration Skill (LOW PRIORITY)
**Purpose:** Help with Django configuration

**Key Features:**
- Generate settings for different environments
- Configure database connections
- Set up caching backends
- Configure logging

**Reference Files:**
- `django/conf/global_settings.py` - Default settings
- `django/conf/__init__.py` - Settings loading

---

### 8. Django Security Skill (LOW PRIORITY)
**Purpose:** Help implement security best practices

**Key Features:**
- CSRF protection patterns
- Authentication setup
- Permission configuration
- Security middleware

**Reference Files:**
- `django/middleware/csrf.py` - CSRF
- `django/contrib/auth/` - Authentication

---

## Proposed Directory Structure

```
.claude/
├── SKILL_CREATION_GUIDE.md          # How to create skills (done)
├── DJANGO_SKILLS_PLAN.md            # This document
│
└── skills/
    ├── django-models/
    │   ├── SKILL.md                  # Main skill file (<500 lines)
    │   ├── scripts/
    │   │   ├── analyze_queries.py    # N+1 detection script
    │   │   ├── generate_model.py     # Model generation
    │   │   └── migration_helper.py   # Migration utilities
    │   └── reference/
    │       ├── field_types.md        # Field type reference
    │       ├── query_patterns.md     # Common query patterns
    │       └── migration_ops.md      # Migration operations
    │
    ├── django-admin/
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   ├── generate_admin.py     # Admin generation
    │   │   └── admin_analyzer.py     # Admin optimization
    │   └── reference/
    │       ├── modeladmin_options.md # All ModelAdmin options
    │       ├── filters.md            # Filter patterns
    │       └── actions.md            # Action patterns
    │
    ├── django-forms/
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   ├── generate_form.py      # Form generation
    │   │   └── validate_form.py      # Validation helper
    │   └── reference/
    │       ├── field_types.md        # Form field types
    │       ├── widgets.md            # Widget options
    │       └── validation.md         # Validation patterns
    │
    ├── django-views/
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   ├── generate_cbv.py       # CBV generation
    │   │   └── url_converter.py      # URL pattern converter
    │   └── reference/
    │       ├── cbv_mixins.md         # Mixin reference
    │       ├── url_patterns.md       # URL pattern guide
    │       └── middleware.md         # Middleware patterns
    │
    ├── django-testing/
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   ├── generate_tests.py     # Test generation
    │   │   └── fixture_builder.py    # Fixture creation
    │   └── reference/
    │       ├── test_classes.md       # Test class hierarchy
    │       ├── assertions.md         # Available assertions
    │       └── fixtures.md           # Fixture patterns
    │
    └── django-commands/
        ├── SKILL.md
        ├── scripts/
        │   └── generate_command.py   # Command scaffold
        └── reference/
            ├── base_classes.md       # Command base classes
            └── argument_patterns.md  # Argument patterns
```

---

## Implementation Priority

### Phase 1: Core Skills (High Impact)
1. **django-models** - Most complex, highest value
2. **django-admin** - High usage, clear patterns
3. **django-forms** - Common pain point

### Phase 2: Development Workflow
4. **django-views** - Essential for development
5. **django-testing** - Quality assurance
6. **django-commands** - Automation

### Phase 3: Configuration
7. **django-settings** - Setup assistance
8. **django-security** - Best practices

---

## Skill Template Structure

Each SKILL.md should follow this structure:

```markdown
# Django [Topic] Skill

## Overview
Brief description of what this skill does and when to use it.

## Quick Start
Common commands and immediate actions.

## Workflows

### Workflow 1: [Name]
Step-by-step instructions for common task.

### Workflow 2: [Name]
Another common workflow.

## Scripts
List of available helper scripts with usage.

## Reference
Links to detailed reference files.

## Examples
Concrete examples (not abstract).

## Common Issues
Troubleshooting for frequent problems.
```

---

## Script Requirements

All scripts should:
1. Be executable standalone
2. Have clear --help documentation
3. Include explicit error handling
4. Use forward slashes for paths
5. Include validation/verification steps
6. Provide clear feedback on success/failure

---

## Key Django Patterns to Encode

### Model Patterns
- Field type selection based on data requirements
- Relationship patterns (ForeignKey, ManyToMany, OneToOne)
- Meta options (ordering, indexes, constraints)
- Custom managers and querysets
- Signal usage patterns

### Admin Patterns
- ModelAdmin configuration hierarchy
- Inline types (Stacked vs Tabular)
- Custom filters and actions
- Permission-based customization
- QuerySet optimization

### Form Patterns
- ModelForm vs Form selection
- Custom validation flow
- Widget selection matrix
- Formset factory patterns
- Error handling

### View Patterns
- CBV mixin composition
- URL converter selection
- Permission decorators
- Content negotiation
- Async views

### Testing Patterns
- Test class hierarchy selection
- Fixture vs setUpTestData
- Client vs RequestFactory
- Query count assertions
- Tag-based organization

### Command Patterns
- BaseCommand vs AppCommand vs LabelCommand
- Argument type selection
- Output styling
- Error handling
- Composition via call_command

---

## Success Metrics

A skill is successful if it:
1. Reduces time to implement common patterns by 50%+
2. Produces idiomatic Django code
3. Includes proper error handling
4. Follows Django's coding conventions
5. Works with current Django version (6.1+)

---

## Next Steps

1. Create skill directory structure
2. Implement django-models skill first (highest impact)
3. Build helper scripts with tests
4. Create reference documentation
5. Iterate based on usage feedback
