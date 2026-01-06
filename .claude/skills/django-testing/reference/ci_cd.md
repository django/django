# CI/CD Testing Patterns for Django

Complete guide to running Django tests in CI/CD pipelines with parallel execution, test sharding, and coverage enforcement.

## Table of Contents

- [GitHub Actions](#github-actions)
- [GitLab CI](#gitlab-ci)
- [Parallel Test Execution](#parallel-test-execution)
- [Test Sharding](#test-sharding)
- [Coverage Enforcement](#coverage-enforcement)
- [Database Configuration](#database-configuration)
- [Caching Dependencies](#caching-dependencies)
- [Matrix Testing](#matrix-testing)
- [Best Practices](#best-practices)

## GitHub Actions

### Basic Django Test Workflow

```yaml
# .github/workflows/test.yml
name: Django Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install coverage

    - name: Run migrations
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
      run: python manage.py migrate

    - name: Run tests with coverage
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
      run: |
        coverage run --source='.' manage.py test
        coverage report --fail-under=80
        coverage xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

### Advanced GitHub Actions with Parallel Tests

```yaml
# .github/workflows/test-parallel.yml
name: Django Tests (Parallel)

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        # Run tests in parallel across 4 workers
        shard: [1, 2, 3, 4]

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db_${{ matrix.shard }}
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
        cache: 'pip'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install coverage pytest-xdist

    - name: Run tests (shard ${{ matrix.shard }}/4)
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db_${{ matrix.shard }}
        REDIS_URL: redis://localhost:6379/0
        SHARD_ID: ${{ matrix.shard }}
        TOTAL_SHARDS: 4
      run: |
        coverage run --source='.' manage.py test \
          --parallel=${{ matrix.shard }} \
          --parallel-total=4

    - name: Upload coverage
      uses: actions/upload-artifact@v3
      with:
        name: coverage-${{ matrix.shard }}
        path: .coverage

  coverage:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install coverage
      run: pip install coverage

    - name: Download all coverage artifacts
      uses: actions/download-artifact@v3

    - name: Combine coverage
      run: |
        coverage combine coverage-*/.coverage
        coverage report --fail-under=80
        coverage xml

    - name: Upload to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Multi-Version Matrix Testing

```yaml
# .github/workflows/test-matrix.yml
name: Django Tests (Matrix)

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.9', '3.10', '3.11', '3.12']
        django-version: ['4.2', '5.0', '5.1']
        exclude:
          # Django 5.0+ requires Python 3.10+
          - python-version: '3.9'
            django-version: '5.0'
          - python-version: '3.9'
            django-version: '5.1'

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install Django==${{ matrix.django-version }}
        pip install -r requirements.txt

    - name: Run tests
      run: python manage.py test

    - name: Run system checks
      run: python manage.py check --fail-level WARNING
```

## GitLab CI

### Basic GitLab CI Configuration

```yaml
# .gitlab-ci.yml
image: python:3.11

variables:
  POSTGRES_DB: test_db
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres
  POSTGRES_HOST: postgres
  DATABASE_URL: postgresql://postgres:postgres@postgres:5432/test_db

services:
  - postgres:15

stages:
  - test
  - coverage

before_script:
  - pip install -r requirements.txt
  - pip install coverage
  - python manage.py migrate

test:
  stage: test
  script:
    - coverage run --source='.' manage.py test
    - coverage report
    - coverage xml
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

lint:
  stage: test
  script:
    - pip install flake8 black isort
    - flake8 .
    - black --check .
    - isort --check-only .
```

### Parallel GitLab CI

```yaml
# .gitlab-ci.yml
image: python:3.11

variables:
  POSTGRES_DB: test_db
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres

.test_template: &test_definition
  stage: test
  services:
    - postgres:15
  before_script:
    - pip install -r requirements.txt coverage
    - python manage.py migrate
  script:
    - |
      coverage run --source='.' manage.py test \
        --parallel=$SHARD_ID \
        --parallel-total=$TOTAL_SHARDS
  artifacts:
    paths:
      - .coverage

test:shard1:
  <<: *test_definition
  variables:
    SHARD_ID: 1
    TOTAL_SHARDS: 4

test:shard2:
  <<: *test_definition
  variables:
    SHARD_ID: 2
    TOTAL_SHARDS: 4

test:shard3:
  <<: *test_definition
  variables:
    SHARD_ID: 3
    TOTAL_SHARDS: 4

test:shard4:
  <<: *test_definition
  variables:
    SHARD_ID: 4
    TOTAL_SHARDS: 4

coverage:
  stage: coverage
  dependencies:
    - test:shard1
    - test:shard2
    - test:shard3
    - test:shard4
  script:
    - pip install coverage
    - coverage combine
    - coverage report --fail-under=80
    - coverage xml
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

## Parallel Test Execution

### Django Built-in Parallel Testing

```bash
# Run tests in parallel (auto-detect CPU count)
python manage.py test --parallel

# Run with specific number of processes
python manage.py test --parallel=4

# With coverage
coverage run --source='.' --concurrency=multiprocessing manage.py test --parallel
coverage combine
coverage report
```

### Configuration for Parallel Tests

```python
# settings/test.py
import os

# Parallel testing database configuration
if 'WORKER_ID' in os.environ:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': f"test_db_{os.environ['WORKER_ID']}",
            'USER': 'postgres',
            'PASSWORD': 'postgres',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'test_db',
            'USER': 'postgres',
            'PASSWORD': 'postgres',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }

# Speed up tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable migrations for faster test DB creation
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

# Uncomment to disable migrations (faster but no migration testing)
# MIGRATION_MODULES = DisableMigrations()

# Use in-memory SQLite for very fast tests (if no PostgreSQL features needed)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': ':memory:',
#     }
# }
```

### pytest-django Parallel Testing

```bash
# Install pytest-xdist
pip install pytest-django pytest-xdist

# Run tests in parallel
pytest -n auto  # Auto-detect CPU count
pytest -n 4     # Use 4 workers

# With coverage
pytest -n auto --cov=myapp --cov-report=xml
```

```python
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = myproject.settings.test
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --reuse-db
    --nomigrations
    -n auto
    --dist loadscope
```

## Test Sharding

### Manual Test Sharding Script

```python
# scripts/shard_tests.py
"""
Distribute tests across multiple CI runners.

Usage:
    python scripts/shard_tests.py --shard=1 --total=4
"""

import sys
import argparse
from django.core.management import call_command
from django.test.runner import DiscoverRunner

def get_test_list():
    """Get all test module paths"""
    runner = DiscoverRunner()
    test_suite = runner.build_suite()

    tests = []
    for test_group in test_suite:
        for test in test_group:
            tests.append(f"{test.__module__}.{test.__class__.__name__}")

    return sorted(set(tests))

def shard_tests(shard_id, total_shards):
    """Divide tests into shards"""
    all_tests = get_test_list()
    total = len(all_tests)

    # Calculate this shard's slice
    shard_size = total // total_shards
    remainder = total % total_shards

    start = (shard_id - 1) * shard_size + min(shard_id - 1, remainder)
    end = start + shard_size + (1 if shard_id <= remainder else 0)

    return all_tests[start:end]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--shard', type=int, required=True)
    parser.add_argument('--total', type=int, required=True)
    args = parser.parse_args()

    if args.shard < 1 or args.shard > args.total:
        print(f"Error: shard must be between 1 and {args.total}")
        sys.exit(1)

    tests = shard_tests(args.shard, args.total)

    print(f"Running shard {args.shard}/{args.total} ({len(tests)} tests)")

    # Run tests for this shard
    call_command('test', *tests, verbosity=2)

if __name__ == '__main__':
    main()
```

### Using Test Sharding in CI

```yaml
# GitHub Actions with manual sharding
- name: Run tests (shard ${{ matrix.shard }})
  run: |
    python scripts/shard_tests.py \
      --shard=${{ matrix.shard }} \
      --total=4
```

## Coverage Enforcement

### Coverage Configuration

```ini
# .coveragerc
[run]
source = .
omit =
    */migrations/*
    */tests/*
    */test_*.py
    manage.py
    */venv/*
    */virtualenv/*
    */__pycache__/*
    */static/*
    */media/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    def __str__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
    @abc.abstractmethod

precision = 2
show_missing = True

[html]
directory = htmlcov

[xml]
output = coverage.xml
```

### Enforce Coverage Thresholds

```yaml
# GitHub Actions
- name: Check coverage
  run: |
    coverage report --fail-under=80

# Fail if specific files drop below threshold
- name: Check critical file coverage
  run: |
    coverage report --include="myapp/critical.py" --fail-under=95
```

### Coverage Reports in Pull Requests

```yaml
# .github/workflows/coverage-comment.yml
name: Coverage Comment

on:
  pull_request:
    branches: [ main ]

jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install coverage

    - name: Run tests with coverage
      run: |
        coverage run --source='.' manage.py test
        coverage xml
        coverage report > coverage.txt

    - name: Comment coverage on PR
      uses: py-cov-action/python-coverage-comment-action@v3
      with:
        GITHUB_TOKEN: ${{ github.token }}
        MINIMUM_GREEN: 90
        MINIMUM_ORANGE: 70
```

## Database Configuration

### PostgreSQL in CI

```yaml
# GitHub Actions
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: test_db
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
    ports:
      - 5432:5432
```

### MySQL in CI

```yaml
services:
  mysql:
    image: mysql:8.0
    env:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: test_db
    options: >-
      --health-cmd="mysqladmin ping"
      --health-interval=10s
      --health-timeout=5s
      --health-retries=3
    ports:
      - 3306:3306
```

### SQLite for Fast Tests

```python
# settings/test.py
# Use SQLite for faster tests if PostgreSQL features not needed
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
```

## Caching Dependencies

### GitHub Actions Cache

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'  # Automatic pip caching

# OR manual caching
- name: Cache pip packages
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-

- name: Cache Django database
  uses: actions/cache@v3
  with:
    path: db.sqlite3
    key: ${{ runner.os }}-db-${{ hashFiles('**/migrations/*.py') }}
```

### GitLab CI Cache

```yaml
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - .cache/pip
    - venv/

before_script:
  - pip install --cache-dir=.cache/pip -r requirements.txt
```

## Matrix Testing

### Test Multiple Django Versions

```yaml
strategy:
  matrix:
    django-version: ['4.2', '5.0', '5.1']
    python-version: ['3.9', '3.10', '3.11', '3.12']

steps:
  - name: Install Django ${{ matrix.django-version }}
    run: pip install Django==${{ matrix.django-version }}
```

### Test Multiple Databases

```yaml
strategy:
  matrix:
    database:
      - engine: postgresql
        image: postgres:15
        port: 5432
      - engine: mysql
        image: mysql:8.0
        port: 3306
      - engine: sqlite
        image: none

steps:
  - name: Set database URL
    run: |
      if [ "${{ matrix.database.engine }}" = "sqlite" ]; then
        echo "DATABASE_URL=sqlite:///db.sqlite3" >> $GITHUB_ENV
      else
        echo "DATABASE_URL=${{ matrix.database.engine }}://..." >> $GITHUB_ENV
      fi
```

## Best Practices

### 1. Optimize Test Speed

```python
# settings/test.py

# Use faster password hasher
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
}

# Use in-memory cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable debug toolbar in tests
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: False,
}
```

### 2. Run Fast Tests First

```yaml
# Run fast linting before slow tests
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install flake8 black
      - run: flake8 .
      - run: black --check .

  test:
    needs: lint  # Only run if linting passes
    runs-on: ubuntu-latest
    steps:
      # ... test steps
```

### 3. Fail Fast on Critical Issues

```yaml
strategy:
  fail-fast: true  # Stop all jobs if one fails
  matrix:
    python-version: ['3.11', '3.12']
```

### 4. Use Test Labels

```python
# Tag slow tests
from django.test import TestCase, tag

@tag('slow')
class SlowIntegrationTests(TestCase):
    def test_expensive_operation(self):
        pass

@tag('fast', 'unit')
class FastUnitTests(TestCase):
    def test_quick_operation(self):
        pass
```

```yaml
# Run only fast tests in PR
- name: Run fast tests
  run: python manage.py test --tag=fast

# Run all tests on main branch
- name: Run all tests
  if: github.ref == 'refs/heads/main'
  run: python manage.py test
```

### 5. Monitor Test Duration

```yaml
- name: Run tests with timing
  run: |
    python manage.py test --timing --verbosity=2 > test_output.txt
    cat test_output.txt

- name: Upload test timing
  uses: actions/upload-artifact@v3
  with:
    name: test-timing
    path: test_output.txt
```

### 6. Retry Flaky Tests

```yaml
- name: Run tests with retry
  uses: nick-invision/retry@v2
  with:
    timeout_minutes: 10
    max_attempts: 3
    command: python manage.py test
```

## Complete Example: Production-Ready CI

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
        cache: 'pip'

    - name: Install linters
      run: |
        pip install flake8 black isort mypy

    - name: Run linters
      run: |
        flake8 . --count --show-source --statistics
        black --check .
        isort --check-only .
        mypy .

  test:
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3, 4]

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
        cache: 'pip'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install coverage

    - name: Run migrations
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
      run: python manage.py migrate

    - name: Run tests (shard ${{ matrix.shard }}/4)
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/0
      run: |
        coverage run --source='.' manage.py test \
          --parallel=${{ matrix.shard }} \
          --parallel-total=4 \
          --timing

    - name: Upload coverage
      uses: actions/upload-artifact@v3
      with:
        name: coverage-${{ matrix.shard }}
        path: .coverage

  coverage:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install coverage
      run: pip install coverage

    - name: Download coverage artifacts
      uses: actions/download-artifact@v3

    - name: Combine coverage
      run: |
        coverage combine coverage-*/.coverage
        coverage report --fail-under=80
        coverage html
        coverage xml

    - name: Upload coverage report
      uses: actions/upload-artifact@v3
      with:
        name: coverage-report
        path: htmlcov/

    - name: Upload to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true

  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Run safety check
      run: |
        pip install safety
        safety check --file requirements.txt

    - name: Run bandit security scan
      run: |
        pip install bandit
        bandit -r . -f json -o bandit-report.json
```

## Summary

**Key CI/CD Patterns:**
- **Parallel execution** - Run tests faster with multiple workers
- **Test sharding** - Distribute tests across CI runners
- **Coverage enforcement** - Maintain code quality standards
- **Matrix testing** - Test multiple Python/Django versions
- **Caching** - Speed up CI with dependency caching
- **Fast failure** - Run quick checks before expensive tests

**Performance Tips:**
- Use PostgreSQL/MySQL services instead of SQLite
- Cache dependencies between runs
- Run linting before tests
- Shard tests across multiple runners
- Use `--parallel` for local speedup

**Coverage Best Practices:**
- Enforce minimum coverage (80%+)
- Exclude migrations and test files
- Generate HTML reports for review
- Fail CI if coverage drops
- Comment coverage on PRs
