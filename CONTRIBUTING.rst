## Contributing to Django

Django is an open‑source web framework that relies on a vibrant community of contributors. Whether you want to fix a typo, improve documentation, add a new feature, or help triage bugs, your contributions are welcome.

---

### Quick links
- **Full contribution guide**: `docs/internals/contributing/` (in the repository) or online at https://docs.djangoproject.com/en/dev/internals/contributing/
- **Code of Conduct**: https://www.djangoproject.com/conduct/
- **File a Trac ticket**: https://code.djangoproject.com/newticket

---

## Overview

Django uses a mixed workflow that combines Trac for ticket tracking with GitHub for code hosting and pull‑request reviews. All substantial changes (anything beyond a simple typo fix) must be associated with a Trac ticket; otherwise the pull request may be closed.

## Setting up a development environment

1. **Fork the repository** on GitHub and clone your fork:
   ```bash
   git clone https://github.com/<your‑username>/django.git
   cd django
   ```
2. **Create a virtual environment** and install the development requirements:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   pip install -r requirements/pytest.txt -r requirements/dev.txt
   ```
3. **Run the test suite** to ensure everything works on your machine:
   ```bash
   ./runtests.sh
   ```
   The suite should complete without failures before you start making changes.

## Making code contributions

1. **Open a Trac ticket** describing the proposed change. Include:
   - A clear title and summary.
   - Why the change is needed (bug, feature request, improvement).
   - Any relevant discussion links.
2. **Create a feature branch** based on the latest `main`:
   ```bash
   git checkout -b my‑feature
   ```
3. **Implement the change** following Django's coding style:
   - Use 4‑space indentation.
   - Follow the existing naming conventions.
   - Add or update tests to cover new behavior.
   - Update documentation where applicable.
4. **Run the test suite** and address any failures.
5. **Commit** with a descriptive message and reference the Trac ticket:
   ```bash
   git commit -m "#12345: Brief summary of change"
   ```
6. **Push** your branch and open a pull request on GitHub. In the PR description, reference the Trac ticket again and summarize the changes.

### Review process

- Automated CI checks (flake8, mypy, test matrix) run on every PR.
- A core developer will review the code, provide feedback, and may request additional tests or documentation.
- Once approvals are received and CI passes, the PR will be merged.

## Documentation contributions

Documentation is treated as first‑class code. Follow these steps:

1. **Locate the relevant file** in the `docs/` directory or the reStructuredText source for the online docs.
2. **Edit the file** using reStructuredText syntax (the rendering on the website is done via Sphinx).
3. **Build the docs locally** to verify formatting:
   ```bash
   cd docs
   make html
   ```
4. **Submit a PR** (a Trac ticket is still required for non‑trivial changes). Small typo fixes may be merged without a ticket, but it is good practice to file one anyway.

## Bug reports and feature requests

- **Bug reports**: Open a Trac ticket describing the issue, steps to reproduce, expected behavior, and Django version.
- **Feature requests**: Open a Trac ticket with a clear rationale and, if possible, a minimal implementation proposal.
- Avoid filing duplicate tickets; search the existing tickets first.

## Code of Conduct

All contributors must adhere to Django's [Code of Conduct](https://www.djangoproject.com/conduct/). The community is committed to a welcoming and inclusive environment. Harassment, discrimination, or any behavior that makes others feel unsafe will not be tolerated.

---

### Additional resources
- **Testing guidelines**: https://docs.djangoproject.com/en/dev/internals/testing/
- **Style guide**: https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/
- **Internationalization**: https://docs.djangoproject.com/en/dev/topics/i18n/

Thank you for helping make Django better!
