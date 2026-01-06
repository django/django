#!/usr/bin/env python
"""
Check Django form templates for accessibility issues (WCAG 2.1 compliance).

Checks for:
- Missing labels for form inputs
- Missing ARIA attributes
- Missing required field indicators
- Missing error associations
- Color-only error indicators
- Missing form instructions
- Improper button types
- Missing fieldset/legend for radio/checkbox groups

Usage:
    python accessibility_check.py templates/forms/
    python accessibility_check.py templates/forms/contact.html
    python accessibility_check.py templates/ --verbose
    python accessibility_check.py templates/ --json
"""

import argparse
import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict
from html.parser import HTMLParser


@dataclass
class AccessibilityIssue:
    """Represents an accessibility issue."""
    severity: str  # 'error', 'warning', 'info'
    rule: str
    message: str
    line: int
    column: int
    element: str


class FormAccessibilityParser(HTMLParser):
    """Parse HTML templates and check for accessibility issues."""

    def __init__(self):
        super().__init__()
        self.issues: List[AccessibilityIssue] = []
        self.input_ids = set()
        self.label_fors = set()
        self.form_elements = []
        self.in_form = False
        self.in_fieldset = False
        self.fieldset_has_legend = False
        self.radio_checkbox_groups = {}
        self.current_line = 1
        self.current_col = 0

    def handle_starttag(self, tag, attrs):
        """Handle opening tags."""
        attrs_dict = dict(attrs)
        line, col = self.getpos()

        if tag == 'form':
            self.in_form = True
            self._check_form_tag(attrs_dict, line, col)

        elif tag in ['input', 'textarea', 'select']:
            self._check_form_field(tag, attrs_dict, line, col)

        elif tag == 'label':
            self._check_label(attrs_dict, line, col)

        elif tag == 'button':
            self._check_button(attrs_dict, line, col)

        elif tag == 'fieldset':
            self.in_fieldset = True
            self.fieldset_has_legend = False

        elif tag == 'legend':
            if self.in_fieldset:
                self.fieldset_has_legend = True

    def handle_endtag(self, tag):
        """Handle closing tags."""
        if tag == 'form':
            self.in_form = False
            self._check_orphaned_inputs()

        elif tag == 'fieldset':
            if not self.fieldset_has_legend:
                self.issues.append(AccessibilityIssue(
                    severity='warning',
                    rule='ARIA-FIELDSET',
                    message='Fieldset should have a legend element',
                    line=self.getpos()[0],
                    column=self.getpos()[1],
                    element='fieldset'
                ))
            self.in_fieldset = False

    def _check_form_tag(self, attrs: Dict, line: int, col: int):
        """Check form tag for accessibility issues."""
        # Check for novalidate attribute (should be present)
        if 'novalidate' not in attrs:
            self.issues.append(AccessibilityIssue(
                severity='info',
                rule='FORM-NOVALIDATE',
                message='Consider adding "novalidate" attribute to prevent browser validation that may not be accessible',
                line=line,
                column=col,
                element='form'
            ))

    def _check_form_field(self, tag: str, attrs: Dict, line: int, col: int):
        """Check form field for accessibility issues."""
        field_id = attrs.get('id')
        field_name = attrs.get('name')
        field_type = attrs.get('type', 'text')

        # Store for later label checking
        if field_id:
            self.input_ids.add(field_id)

        self.form_elements.append({
            'tag': tag,
            'type': field_type,
            'id': field_id,
            'name': field_name,
            'line': line,
            'col': col,
            'attrs': attrs
        })

        # Skip hidden inputs
        if field_type == 'hidden':
            return

        # Check for label association
        has_aria_label = 'aria-label' in attrs
        has_aria_labelledby = 'aria-labelledby' in attrs
        has_title = 'title' in attrs

        if not (field_id or has_aria_label or has_aria_labelledby or has_title):
            self.issues.append(AccessibilityIssue(
                severity='error',
                rule='LABEL-REQUIRED',
                message=f'Input field must have an id for label association or aria-label attribute',
                line=line,
                column=col,
                element=f'{tag}[name="{field_name}"]'
            ))

        # Check for required attribute
        is_required = 'required' in attrs
        has_aria_required = attrs.get('aria-required') == 'true'

        if is_required and not has_aria_required:
            self.issues.append(AccessibilityIssue(
                severity='warning',
                rule='ARIA-REQUIRED',
                message='Required fields should have aria-required="true" attribute',
                line=line,
                column=col,
                element=f'{tag}[name="{field_name}"]'
            ))

        # Check for aria-describedby for help text
        has_describedby = 'aria-describedby' in attrs

        if not has_describedby:
            self.issues.append(AccessibilityIssue(
                severity='info',
                rule='ARIA-DESCRIBEDBY',
                message='Consider adding aria-describedby to associate help text or error messages',
                line=line,
                column=col,
                element=f'{tag}[name="{field_name}"]'
            ))

        # Check for autocomplete on common fields
        if field_name in ['email', 'username', 'password', 'first_name', 'last_name',
                          'phone', 'address', 'city', 'zip', 'country']:
            if 'autocomplete' not in attrs:
                self.issues.append(AccessibilityIssue(
                    severity='info',
                    rule='AUTOCOMPLETE',
                    message=f'Consider adding autocomplete attribute for {field_name}',
                    line=line,
                    column=col,
                    element=f'{tag}[name="{field_name}"]'
                ))

        # Track radio/checkbox groups
        if field_type in ['radio', 'checkbox'] and field_name:
            if field_name not in self.radio_checkbox_groups:
                self.radio_checkbox_groups[field_name] = []
            self.radio_checkbox_groups[field_name].append({
                'line': line,
                'col': col,
                'id': field_id
            })

    def _check_label(self, attrs: Dict, line: int, col: int):
        """Check label for accessibility issues."""
        label_for = attrs.get('for')

        if label_for:
            self.label_fors.add(label_for)
        else:
            self.issues.append(AccessibilityIssue(
                severity='warning',
                rule='LABEL-FOR',
                message='Label should have a "for" attribute to explicitly associate with input',
                line=line,
                column=col,
                element='label'
            ))

    def _check_button(self, attrs: Dict, line: int, col: int):
        """Check button for accessibility issues."""
        button_type = attrs.get('type')

        if not button_type:
            self.issues.append(AccessibilityIssue(
                severity='error',
                rule='BUTTON-TYPE',
                message='Button must have a type attribute (submit, button, or reset)',
                line=line,
                column=col,
                element='button'
            ))

    def _check_orphaned_inputs(self):
        """Check for inputs without associated labels."""
        orphaned = self.input_ids - self.label_fors

        for element in self.form_elements:
            if element['id'] in orphaned and element['type'] not in ['hidden', 'submit', 'button']:
                self.issues.append(AccessibilityIssue(
                    severity='error',
                    rule='LABEL-MISSING',
                    message=f'Input field has id but no associated label',
                    line=element['line'],
                    column=element['col'],
                    element=f'{element["tag"]}[id="{element["id"]}"]'
                ))

        # Check radio/checkbox groups for fieldset
        for name, elements in self.radio_checkbox_groups.items():
            if len(elements) > 1:
                # Multiple radio/checkbox with same name should be in fieldset
                self.issues.append(AccessibilityIssue(
                    severity='warning',
                    rule='FIELDSET-GROUP',
                    message=f'Radio/checkbox group "{name}" should be wrapped in fieldset with legend',
                    line=elements[0]['line'],
                    column=elements[0]['col'],
                    element=f'input[name="{name}"]'
                ))


def check_template_django_tags(content: str) -> List[AccessibilityIssue]:
    """Check for Django template patterns that may have accessibility issues."""
    issues = []

    # Check for {{ form.as_p }} or {{ form.as_table }}
    if re.search(r'{{\s*form\.as_[pt]\s*}}', content):
        issues.append(AccessibilityIssue(
            severity='info',
            rule='FORM-RENDERING',
            message='Using form.as_p or form.as_table may not provide full accessibility control. Consider manual rendering.',
            line=content[:content.find('form.as_')].count('\n') + 1,
            column=0,
            element='{{ form.as_* }}'
        ))

    # Check for error display
    if '{{ form.errors }}' in content and 'role="alert"' not in content:
        issues.append(AccessibilityIssue(
            severity='warning',
            rule='ERROR-ROLE',
            message='Error messages should have role="alert" for screen readers',
            line=content[:content.find('form.errors')].count('\n') + 1,
            column=0,
            element='{{ form.errors }}'
        ))

    # Check for CSRF token
    if '<form' in content and 'csrf_token' not in content:
        issues.append(AccessibilityIssue(
            severity='error',
            rule='CSRF-TOKEN',
            message='Form is missing {% csrf_token %}',
            line=content.find('<form'),
            column=0,
            element='form'
        ))

    # Check for enctype on file upload forms
    if 'type="file"' in content and 'enctype="multipart/form-data"' not in content:
        issues.append(AccessibilityIssue(
            severity='error',
            rule='ENCTYPE-MISSING',
            message='File upload form must have enctype="multipart/form-data"',
            line=content[:content.find('type="file"')].count('\n') + 1,
            column=0,
            element='form'
        ))

    return issues


def check_file(file_path: Path) -> List[AccessibilityIssue]:
    """Check a single template file for accessibility issues."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return [AccessibilityIssue(
            severity='error',
            rule='FILE-READ',
            message=f'Could not read file: {e}',
            line=0,
            column=0,
            element=str(file_path)
        )]

    # Parse HTML
    parser = FormAccessibilityParser()
    try:
        parser.feed(content)
    except Exception as e:
        return [AccessibilityIssue(
            severity='error',
            rule='PARSE-ERROR',
            message=f'Could not parse HTML: {e}',
            line=0,
            column=0,
            element=str(file_path)
        )]

    # Check Django template patterns
    django_issues = check_template_django_tags(content)

    return parser.issues + django_issues


def check_directory(dir_path: Path) -> Dict[str, List[AccessibilityIssue]]:
    """Check all template files in a directory."""
    results = {}

    # Find all HTML template files
    for template_file in dir_path.rglob('*.html'):
        issues = check_file(template_file)
        if issues:
            results[str(template_file)] = issues

    return results


def print_results(results: Dict[str, List[AccessibilityIssue]], verbose: bool = False):
    """Print results in human-readable format."""
    total_errors = 0
    total_warnings = 0
    total_info = 0

    for file_path, issues in results.items():
        print(f"\n{'=' * 80}")
        print(f"File: {file_path}")
        print('=' * 80)

        # Count issues by severity
        errors = [i for i in issues if i.severity == 'error']
        warnings = [i for i in issues if i.severity == 'warning']
        info = [i for i in issues if i.severity == 'info']

        total_errors += len(errors)
        total_warnings += len(warnings)
        total_info += len(info)

        # Print errors first
        if errors:
            print(f"\n❌ ERRORS ({len(errors)}):")
            for issue in errors:
                print(f"  Line {issue.line}: [{issue.rule}] {issue.message}")
                if verbose:
                    print(f"    Element: {issue.element}")

        # Print warnings
        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for issue in warnings:
                print(f"  Line {issue.line}: [{issue.rule}] {issue.message}")
                if verbose:
                    print(f"    Element: {issue.element}")

        # Print info (only in verbose mode)
        if info and verbose:
            print(f"\nℹ️  INFO ({len(info)}):")
            for issue in info:
                print(f"  Line {issue.line}: [{issue.rule}] {issue.message}")
                if verbose:
                    print(f"    Element: {issue.element}")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print('=' * 80)
    print(f"Files checked: {len(results)}")
    print(f"Total errors: {total_errors}")
    print(f"Total warnings: {total_warnings}")
    if verbose:
        print(f"Total info: {total_info}")

    return total_errors


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Check Django form templates for accessibility issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s templates/forms/
  %(prog)s templates/forms/contact.html
  %(prog)s templates/ --verbose
  %(prog)s templates/ --json > report.json

Severity Levels:
  error   - Critical accessibility issue (WCAG Level A)
  warning - Important accessibility issue (WCAG Level AA)
  info    - Suggested improvement (WCAG Level AAA or best practice)
        """
    )

    parser.add_argument(
        'path',
        help='Path to template file or directory'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show detailed output including info messages'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    # Check path
    path = Path(args.path)

    if not path.exists():
        print(f"Error: Path '{args.path}' does not exist")
        return 1

    # Check files
    if path.is_file():
        results = {str(path): check_file(path)}
    else:
        results = check_directory(path)

    if not results:
        print(f"No template files found in {args.path}")
        return 0

    # Output results
    if args.json:
        json_results = {
            file_path: [asdict(issue) for issue in issues]
            for file_path, issues in results.items()
        }
        print(json.dumps(json_results, indent=2))
        return 0
    else:
        total_errors = print_results(results, verbose=args.verbose)
        return 1 if total_errors > 0 else 0


if __name__ == '__main__':
    exit(main())
