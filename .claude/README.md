# Django Claude Skills

Welcome to the Django Claude Skills system - a comprehensive toolkit for building Django applications with AI assistance.

## Quick Links

### Core Documentation
- [Skills Index](SKILLS_INDEX.md) - Find the right skill for your task
- [Skills Plan](DJANGO_SKILLS_PLAN.md) - Overall architecture and roadmap
- [Improvement Plan](SKILLS_IMPROVEMENT_PLAN.md) - Enhancement priorities
- [Skill Creation Guide](SKILL_CREATION_GUIDE.md) - How to create new skills

### Shared Infrastructure
- [Django Analyzer](skills/_shared/django_analyzer.py) - Project structure analysis
- [Code Generator](skills/_shared/code_generator.py) - Template-based code generation
- [Validators](skills/_shared/validators.py) - Django code validation utilities

## Getting Started

### Prerequisites
- Django 5.0 or higher
- Python 3.10 or higher
- Claude CLI installed

### Using a Skill

Skills are organized by Django component and task type. To use a skill:

1. **Find the right skill**: Check [SKILLS_INDEX.md](SKILLS_INDEX.md) for task-based lookup
2. **Read the skill documentation**: Each skill has comprehensive docs in `skills/[skill-name]/SKILL.md`
3. **Run the skill scripts**: Skills provide Python utilities in `skills/[skill-name]/scripts/`
4. **Reference patterns**: Check `skills/[skill-name]/reference/` for best practices

### Quick Start Examples

#### Analyzing Your Django Project
```bash
python .claude/skills/_shared/django_analyzer.py /path/to/your/project
```

#### Validating a Model
```python
from skills._shared.validators import validate_model_definition

errors = validate_model_definition(model_code)
if errors:
    print("Validation errors:", errors)
```

#### Generating Code from Templates
```python
from skills._shared.code_generator import DjangoCodeGenerator

generator = DjangoCodeGenerator()
code = generator.render_template('model.py.jinja', context={
    'model_name': 'Article',
    'fields': [
        {'name': 'title', 'type': 'CharField', 'max_length': 200},
        {'name': 'content', 'type': 'TextField'}
    ]
})
```

## Available Skills

### Phase 1: Foundation (Released)
- **django-models** - Model creation, migrations, ORM queries, async support
- **django-testing** - Test classes, fixtures, async testing, CI/CD patterns
- **django-forms** - Form creation, validation, widgets, frontend integration

### Phase 2: Core Features (In Development)
- **django-admin** - Admin customization, permissions, UX patterns
- **django-views** - FBV/CBV patterns, async views, file handling
- **django-templates** - Template tags, filters, inheritance, optimization

### Phase 3: Infrastructure (Planned)
- **django-signals** - Signal creation, handlers, debugging, anti-patterns
- **django-commands** - Management commands, async support, progress reporting
- **django-caching** - Cache strategies, invalidation, Redis/Memcached

### Phase 4: Advanced (Planned)
- **django-settings** - Configuration management, environment-specific settings
- **django-middleware** - Custom middleware, request/response processing
- **django-urls** - URL patterns, routing, namespacing

## Architecture

### Skill Structure
```
.claude/
├── README.md                    # This file
├── SKILLS_INDEX.md              # Searchable directory
├── DJANGO_SKILLS_PLAN.md        # Overall plan
├── SKILLS_IMPROVEMENT_PLAN.md   # Enhancement priorities
├── SKILL_CREATION_GUIDE.md      # Creation guidelines
│
├── skills/
│   ├── _shared/                 # Common utilities
│   │   ├── django_analyzer.py   # Project analysis
│   │   ├── code_generator.py    # Code generation
│   │   └── validators.py        # Validation utilities
│   │
│   ├── _examples/               # Unified example project
│   │   └── blog-app/
│   │
│   └── [skill-name]/            # Individual skills
│       ├── SKILL.md             # Main documentation
│       ├── scripts/             # Automation scripts
│       ├── reference/           # Pattern documentation
│       └── examples/            # Code examples
│
└── maintenance/
    ├── CHANGELOG.md
    └── DJANGO_COMPATIBILITY.md
```

### Shared Utilities

#### Django Analyzer (`django_analyzer.py`)
Analyzes Django project structure and extracts metadata:
- Detects installed apps
- Finds models, views, forms
- Analyzes database configuration
- Detects async patterns
- Returns structured JSON output

#### Code Generator (`code_generator.py`)
Template-based code generation utilities:
- Jinja2 template rendering
- Django-specific formatting
- Import statement management
- Common generation patterns
- PEP 8 compliance

#### Validators (`validators.py`)
Validation utilities for Django code:
- Model field validation
- Form field validation
- URL pattern validation
- Migration validation
- Django system check integration

## Design Principles

### 1. Task-Oriented
Skills are organized around developer tasks, not just Django concepts:
- "I need to add a field to my model" → django-models
- "I need to debug slow queries" → django-models (N+1 detection)
- "I need to test async views" → django-testing + django-views

### 2. Progressive Disclosure
Each skill provides multiple levels of detail:
- **Quick Start**: 3-step common workflow
- **Core Workflows**: Step-by-step guides
- **Reference**: Comprehensive patterns
- **Advanced**: Edge cases and optimization

### 3. Real-World Focus
Skills prioritize actual developer needs:
- Concrete examples over abstract concepts
- Common pain points addressed explicitly
- Production-ready patterns
- Security integrated throughout

### 4. Version Awareness
All skills are compatible with Django 5.0+:
- Version-specific notes included
- Async patterns throughout
- Modern best practices
- Deprecation warnings

## Token Budget Guidelines

To ensure skills work effectively with Claude:

- **SKILL.md**: ≤40k tokens
- **Reference files**: ≤50k tokens each
- **Total loaded**: ≤100k tokens per session
- **Scripts**: Include docstrings and type hints

## Success Metrics

Skills are validated against measurable criteria:

| Metric | Target |
|--------|--------|
| Generated code passes flake8/mypy | 100% |
| Test coverage for skill scripts | ≥80% |
| Django system checks pass | 0 warnings |
| Script execution time | <5 seconds |
| Reference coverage | ≥90% of Django module |
| Examples per skill | ≥5 concrete examples |

## Contributing

### Creating a New Skill

1. Read [SKILL_CREATION_GUIDE.md](SKILL_CREATION_GUIDE.md)
2. Use the skill template structure
3. Include all required sections
4. Add validation scripts
5. Test with real projects
6. Update SKILLS_INDEX.md

### Improving Existing Skills

1. Check [SKILLS_IMPROVEMENT_PLAN.md](SKILLS_IMPROVEMENT_PLAN.md) for priorities
2. Follow the enhancement guidelines
3. Maintain backward compatibility
4. Update documentation
5. Add tests for new patterns

## Security

Security is integrated into each skill, not treated separately:

- **Forms**: CSRF, XSS prevention, file upload validation
- **Views**: Authentication, authorization, open redirect prevention
- **Models**: SQL injection prevention, secure defaults
- **Admin**: Object-level permissions, audit trails
- **Commands**: Input validation, path sanitization

## Support

### Common Issues

**Skill not found**: Check SKILLS_INDEX.md for correct skill name

**Import errors**: Ensure you're using Django 5.0+ and Python 3.10+

**Script execution fails**: Check that paths are absolute and files exist

**Generated code fails checks**: Review the skill's validation section

### Getting Help

1. Check the skill's troubleshooting section
2. Review related skills for dependencies
3. Consult the improvement plan for known limitations
4. Check Django version compatibility notes

## Roadmap

See [DJANGO_SKILLS_PLAN.md](DJANGO_SKILLS_PLAN.md) for:
- Detailed phase breakdown
- Timeline estimates
- Priority ordering
- Success criteria per phase

See [SKILLS_IMPROVEMENT_PLAN.md](SKILLS_IMPROVEMENT_PLAN.md) for:
- Coverage gaps
- Enhancement priorities
- Expert review findings
- Specific improvement recommendations

## License

These skills are designed to work with the Django project and follow Django's licensing.
