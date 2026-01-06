# Django Skills Improvement Plan

Based on comprehensive review by 14 specialized subagents, this document outlines critical improvements needed for the Django Skills plan.

---

## Executive Summary

The current plan covers **20-40% of actual Django complexity**. Major gaps exist in:
- Async support across all skills
- Security integration (should not be separate)
- Frontend/UX patterns
- CI/CD automation
- Real-world use cases vs. generic scaffolding

---

## Critical Structural Changes

### 1. Add Missing Skill Areas

| New Skill | Priority | Justification |
|-----------|----------|---------------|
| **django-templates** | HIGH | Core MTV component, heavily used |
| **django-signals** | HIGH | Decoupling pattern, common integration point |
| **django-caching** | MEDIUM | Performance critical |

### 2. Reprioritize Existing Skills

**Current → Recommended:**
```
Phase 1 (Foundation):
  1. django-models      (unchanged)
  2. django-testing     (MOVE UP from Phase 2)
  3. django-forms       (unchanged)

Phase 2 (Core Features):
  4. django-admin       (unchanged)
  5. django-views       (split: FBV + CBV)
  6. django-templates   (NEW)

Phase 3 (Infrastructure):
  7. django-signals     (NEW)
  8. django-commands    (unchanged)
  9. django-caching     (NEW)

Phase 4 (Foundational - Move UP):
  10. django-settings   (WAS: Low priority)
  11. django-security   (INTEGRATE into other skills, not separate)
```

### 3. Create Cross-Skill Infrastructure

```
.claude/
├── README.md                    # NEW: Discovery guide
├── SKILLS_INDEX.md              # NEW: Searchable directory
├── skills/
│   ├── _shared/                 # NEW: Common utilities
│   │   ├── django_analyzer.py
│   │   ├── code_generator.py
│   │   └── validators.py
│   ├── _examples/               # NEW: Unified example project
│   │   └── blog-app/
│   └── [skill folders...]
└── maintenance/
    ├── CHANGELOG.md
    └── DJANGO_COMPATIBILITY.md
```

---

## Skill-by-Skill Improvements

### Django Models & ORM (Currently 20% coverage → Target 80%)

**Add Pain Points:**
- Async ORM operations (Django 4.1+) - 40% of new projects use async
- Multi-table inheritance pitfalls
- Signal anti-patterns
- Raw SQL injection risks
- Lazy relationship loading complexity

**Add Reference Files:**
```
reference/
├── async_orm_patterns.md       # NEW
├── expressions.md              # NEW (F, Q, Case, Window, Subquery)
├── signals.md                  # NEW
├── lookups.md                  # NEW
├── constraints.md              # NEW
├── deletion.md                 # NEW (cascade behavior)
├── inheritance_guide.md        # NEW
├── related_descriptors.md      # NEW
└── sql_compiler.md             # NEW
```

**Add Scripts:**
```
scripts/
├── analyze_n_plus_one.py       # Detect N+1 queries
├── convert_to_async.py         # Async ORM conversion
├── detect_lazy_loading.py      # Find lazy loading issues
├── analyze_mti_complexity.py   # Multi-table inheritance
├── map_signal_dependencies.py  # Signal chains
├── debug_query_compilation.py  # Query debugging
└── check_raw_sql_safety.py     # SQL injection detection
```

**Add Workflows:**
- "Add field to model with existing data" (daily use)
- "Debug slow query" (multiple times/week)
- "Resolve migration conflicts" (team environments)
- "Safe bulk data migration"

---

### Django Admin (Currently 50% coverage → Target 90%)

**Add Missing Features:**
- Object-level permissions (not just model-level)
- Custom admin views via `get_urls()`
- Multi-database admin support
- Admin actions with forms
- Facets/filtering (Django 6.0+)
- Autocomplete customization
- LogEntry/audit trail customization

**Add Reference Files:**
```
reference/
├── permissions_matrix.md       # NEW
├── custom_views.md             # NEW
├── query_optimization.md       # NEW
├── autocomplete.md             # NEW
├── decorators.md               # NEW (@admin.display, @action)
├── widgets.md                  # NEW (21 widget types)
├── admin_site.md               # NEW (custom AdminSite)
├── inlines.md                  # NEW (advanced patterns)
├── logging.md                  # NEW (audit trails)
├── facets.md                   # NEW (Django 6.0+)
└── bulk_operations.md          # NEW
```

**Add UX-Focused Features:**
- Widget selection matrix (field type → widget)
- Search/filter optimization patterns
- Mobile-responsive admin templates
- JavaScript integration (autocomplete, cascading)
- CSS framework integration

---

### Django Forms (Currently 40% coverage → Target 85%)

**Add Missing Validation Patterns:**
- Cross-field validation
- Async validation workarounds
- File upload validation (MIME, malware)
- Multi-step form wizards
- Dynamic form fields
- Form security (CSRF/XSS - don't separate!)

**Add Frontend Integration:**
```
reference/
├── css_framework_integration.md   # Bootstrap/Tailwind
├── form_rendering.md              # Template strategies
├── javascript_integration.md      # Client-side validation
├── ajax_patterns.md               # Async submission
├── accessibility_checklist.md     # WCAG compliance
├── user_experience.md             # UX best practices
├── drf_integration.md             # API serializers
├── cross_field_validation.md      # NEW
├── modelform_validation.md        # NEW (dual validation)
└── file_upload_patterns.md        # NEW
```

---

### Django Views & URLs (Currently 30% coverage → Target 80%)

**Add Missing Patterns:**
- REST API without DRF (JsonResponse patterns)
- File downloads/uploads
- Pagination patterns
- Session handling
- Flash messages
- Request/response lifecycle documentation
- View-level caching (@cache_page, @etag)
- Rate limiting
- Async views guide

**Add Reference Files:**
```
reference/
├── api_patterns.md             # NEW (REST without DRF)
├── file_handling.md            # NEW
├── pagination.md               # NEW
├── session_management.md       # NEW
├── messages_framework.md       # NEW
├── caching.md                  # NEW
├── rate_limiting.md            # NEW
├── async_views.md              # NEW
├── mixin_composition.md        # NEW (decision matrix)
├── request_lifecycle.md        # NEW
└── security_patterns.md        # NEW (CSRF, open redirect)
```

**Reprioritize:** Move Views to HIGH priority (currently MEDIUM)

---

### Django Testing (Currently 30-40% coverage → Target 85%)

**Add Missing Test Patterns:**
- Test class hierarchy (SimpleTestCase vs TestCase vs TransactionTestCase)
- Async testing (AsyncClient, async test methods)
- Database transaction testing
- Mocking strategies (external services, time)
- Factory patterns (factory_boy)
- Coverage reporting integration

**Add CI/CD Patterns:**
```
reference/
├── test_classes.md             # Full hierarchy
├── async_testing.md            # NEW
├── database_testing.md         # NEW (transactions, multi-db)
├── mocking.md                  # NEW
├── query_optimization.md       # NEW (N+1 detection)
├── coverage.md                 # NEW
├── ci_cd_pipelines.md          # NEW (GitHub Actions)
├── parallel_testing.md         # NEW
├── flaky_test_patterns.md      # NEW
└── test_environment_config.md  # NEW
```

**Add Scripts:**
```
scripts/
├── parallel_test_config.py     # DB isolation for parallel
├── shard_tests.py              # Distribute across runners
├── flaky_test_detector.py      # Identify intermittent failures
├── detect_slow_tests.py        # Performance regression
├── performance_baseline.py     # Track metrics
└── generate_test_env.py        # .env.test templates
```

---

### Django Management Commands (Currently 60% coverage → Target 90%)

**Add Missing Patterns:**
- Long-running commands with progress reporting
- Database transactions in commands
- Dry-run and preview modes
- Interactive confirmation patterns
- Async management commands
- Memory-efficient iteration (QuerySet.iterator)
- Output modes for CI/CD (--scriptable)
- File I/O with concurrent.futures

**Add Use-Case-Specific Templates:**
```
scripts/
├── generate_import_command.py      # CSV/bulk data import
├── generate_maintenance_command.py # Cleanup/deletion
├── generate_report_command.py      # Analytics
├── generate_integration_command.py # API sync
└── generate_debug_command.py       # Inspection
```

**Add Reference Files:**
```
reference/
├── progress_reporting.md       # NEW
├── async_commands.md           # NEW
├── database_patterns.md        # NEW
├── interactive_patterns.md     # NEW
├── memory_efficiency.md        # NEW
├── file_operations.md          # NEW
├── testing_commands.md         # NEW
└── decorators_context.md       # NEW (@no_translations)
```

---

## Skill Template Improvements

**Current → Enhanced Template:**

```markdown
# Django [Topic] Skill

## Overview
[What and when to use]

## Quick Start
[3-step most common workflow]

## When to Use This Skill
[Decision tree/checklist]

## Core Workflows
### Workflow 1: [Name]
[Step-by-step]

## Scripts & Tools
[With input/output specifications]

## Common Patterns
[Best practices with code]

## Anti-Patterns                    # NEW
[What NOT to do]

## Edge Cases & Gotchas             # NEW
[Specific issues]

## Related Skills                   # NEW
[Dependencies and complements]

## Django Version Notes             # NEW
[Version-specific changes]

## Examples
[Concrete, not abstract]

## Troubleshooting                  # NEW
[Common errors and solutions]
```

---

## Success Metrics Improvements

**Replace vague metrics with measurable ones:**

| Metric | Target |
|--------|--------|
| Generated code passes flake8/mypy | 100% |
| Test coverage for skill scripts | ≥80% |
| Django system checks pass | 0 warnings |
| Script execution time | <5 seconds |
| Reference coverage | ≥90% of Django module |
| Examples per skill | ≥5 concrete examples |

---

## Documentation Improvements

### Add to SKILL_CREATION_GUIDE.md:

1. **Token Budget Management**
   - SKILL.md: ≤40k tokens
   - Reference files: ≤50k each
   - Total loaded: ≤100k tokens

2. **Error Recovery Patterns**
   - Input validation before processing
   - Specific error messages with recovery steps
   - Graceful degradation for edge cases

3. **Script Interface Specifications**
   - Input format (file path, JSON, etc.)
   - Output format (JSON, code, report)
   - Exit codes (0=success, 1=user error, 2=system error)

4. **Security Checklist**
   - No hardcoded secrets
   - Input validation
   - Path sanitization
   - No shell execution of user input

5. **Maintenance Strategy**
   - Version per skill
   - Django compatibility matrix
   - Deprecation policy

---

## Implementation Priority

### Immediate (Before First Skill):
1. Add token budget guidance
2. Define script interface specifications
3. Create validation criteria per skill
4. Add error recovery patterns
5. Integrate security into each skill (not separate)

### Phase 1 Enhancement:
1. Expand django-models to 80% coverage
2. Add async patterns throughout
3. Create unified example project
4. Add cross-skill references

### Phase 2 Enhancement:
1. Add django-templates skill
2. Add django-signals skill
3. Enhance testing with CI/CD patterns
4. Add frontend integration to forms

### Phase 3 Enhancement:
1. Add django-caching skill
2. Create maintenance infrastructure
3. Add feedback collection mechanism
4. Django version compatibility matrix

---

## Key Takeaways from Reviews

1. **Plan covers basics but misses real-world complexity** - Need more workflows for daily developer tasks
2. **Security should be integrated, not separate** - CSRF, XSS belong in Forms; auth belongs in Views
3. **Async is critical** - 40% of new projects use async; every skill needs async patterns
4. **Frontend matters** - Forms and Admin need CSS/JS integration patterns
5. **CI/CD is essential** - Testing skill needs parallel execution, coverage, pipeline templates
6. **Concrete > Abstract** - Replace generic scaffolds with use-case-specific generators
7. **Metrics must be measurable** - Replace "50% time savings" with testable criteria
