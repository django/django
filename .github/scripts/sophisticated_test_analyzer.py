import json
import sys
import re
from typing import List


class DjangoModuleMapper:
    """Maps Django modules to their corresponding test directories"""
    
    # Comprehensive mapping of Django modules to test directories
    MODULE_TO_TEST_MAPPING = {
        # Admin
        'django/contrib/admin/': [
            'tests/admin_changelist/',
            'tests/admin_custom_urls/',
            'tests/admin_docs/',
            'tests/admin_filters/',
            'tests/admin_inlines/',
            'tests/admin_ordering/',
            'tests/admin_registration/',
            'tests/admin_utils/',
            'tests/admin_views/',
            'tests/admin_widgets/',
        ],
        
        # Authentication & Authorization
        'django/contrib/auth/': [
            'tests/auth_tests/',
            'tests/contenttypes_tests/',
        ],
        
        # Database & Models
        'django/db/models/': [
            'tests/model_*/',
            'tests/queries/',
            'tests/aggregation*/',
            'tests/annotations/',
            'tests/generic_relations/',
            'tests/lookup/',
            'tests/expressions*/',
            'tests/field_*/',
            'tests/custom_pk/',
            'tests/validation/',
        ],
        
        'django/db/': [
            'tests/backends/',
            'tests/db_*/',
            'tests/introspection/',
            'tests/migrations*/',
            'tests/schema/',
            'tests/transactions/',
        ],
        
        # Forms
        'django/forms/': [
            'tests/forms_tests/',
            'tests/model_forms/',
        ],
        
        # Templates
        'django/template/': [
            'tests/template_tests/',
        ],
        
        # URLs
        'django/urls/': [
            'tests/urlpatterns*/',
            'tests/view_tests/',
            'tests/generic_views/',
        ],
        
        # Management Commands
        'django/core/management/': [
            'tests/admin_scripts/',
            'tests/user_commands/',
        ],
        
        # Core utilities
        'django/core/': [
            'tests/cache/',
            'tests/checks/',
            'tests/files/',
            'tests/mail/',
            'tests/serializers/',
            'tests/signing/',
            'tests/validators/',
        ],
        
        # HTTP & Views
        'django/http/': [
            'tests/requests/',
            'tests/responses/',
            'tests/view_tests/',
        ],
        
        'django/views/': [
            'tests/generic_views/',
            'tests/view_tests/',
        ],
        
        # Utilities
        'django/utils/': [
            'tests/utils_tests/',
        ],
        
        # Sessions
        'django/contrib/sessions/': [
            'tests/sessions_tests/',
        ],
        
        # Messages
        'django/contrib/messages/': [
            'tests/messages_tests/',
        ],
        
        # Static files
        'django/contrib/staticfiles/': [
            'tests/staticfiles_tests/',
        ],
        
        # Content types
        'django/contrib/contenttypes/': [
            'tests/contenttypes_tests/',
        ],
        
        # Sites framework
        'django/contrib/sites/': [
            'tests/sites_tests/',
        ],
    }
    
    @classmethod
    def get_expected_test_dirs(cls, django_file: str) -> List[str]:
        """Get expected test directories for a Django file"""
        for module_path, test_dirs in cls.MODULE_TO_TEST_MAPPING.items():
            if django_file.startswith(module_path):
                return test_dirs
        return []


class CodeChangeAnalyzer:
    """Analyzes code changes to determine if tests are needed"""
    
    @staticmethod
    def is_trivial_change(file_data: dict) -> bool:
        """Determine if a change is trivial and doesn't need tests"""
        filename = file_data['filename']
        patch = file_data.get('patch', '')
        
        # Documentation files
        if any(filename.endswith(ext) for ext in ['.txt', '.rst', '.md']):
            return True
        
        # Migration files
        if '/migrations/' in filename:
            return True
        
        # Only whitespace/comment changes
        if patch:
            meaningful_lines = []
            for line in patch.split('\n'):
                if line.startswith(('+', '-')) and not line.startswith(('+++', '---')):
                    stripped = line[1:].strip()
                    # Skip empty lines, comments, docstrings
                    if (stripped and 
                        not stripped.startswith('#') and 
                        not stripped.startswith('"""') and
                        not stripped.startswith("'''")):
                        meaningful_lines.append(stripped)
            
            # If no meaningful changes, it's trivial
            if not meaningful_lines:
                return True
        
        return False
    
    @staticmethod
    def has_new_functions_or_classes(file_data: dict) -> bool:
        """Check if new functions or classes were added"""
        patch = file_data.get('patch', '')
        if not patch:
            return False
        
        added_lines = []
        for line in patch.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:])
        
        added_code = '\n'.join(added_lines)
        
        # Look for new function/class definitions
        new_defs = re.findall(r'^\s*(def|class)\s+(\w+)', added_code, re.MULTILINE)
        public_defs = [name for def_type, name in new_defs if not name.startswith('_')]
        
        return len(public_defs) > 0
    
    @staticmethod
    def modifies_existing_logic(file_data: dict) -> bool:
        """Check if existing logic was modified (not just additions)"""
        patch = file_data.get('patch', '')
        if not patch:
            return False
        
        # Count modified lines (both additions and deletions in same area)
        deletions = len([l for l in patch.split('\n') if l.startswith('-') and not l.startswith('---')])
        additions = len([l for l in patch.split('\n') if l.startswith('+') and not l.startswith('+++')])
        
        # If there are both additions and deletions, likely logic modification
        return deletions > 0 and additions > 0
    
    @staticmethod
    def is_bug_fix(title: str, body: str) -> bool:
        """Enhanced bug fix detection"""
        text = f"{title} {body}".lower()
        
        bug_patterns = [
            r'\bfix(es|ed)?\b.*#\d+',
            r'#\d+.*\bfix(es|ed)?\b',
            r'\b(bug|issue)\b.*#\d+',
            r'#\d+.*\b(bug|issue)\b',
            r'\b(resolv(es|ed)|clos(es|ed))\b.*#\d+',
            r'regression.*fix',
            r'fix.*regression',
        ]
        
        return any(re.search(pattern, text) for pattern in bug_patterns)
    
    @staticmethod
    def is_new_feature(title: str, body: str) -> bool:
        """Detect new features"""
        text = f"{title} {body}".lower()
        
        feature_patterns = [
            r'\badd(s|ed)?\b.*feature',
            r'\bnew\b.*feature',
            r'\bimplement(s|ed)?\b',
            r'\bintroduc(es|ed)\b',
            r'\benhance(s|d|ment)?\b',
        ]
        
        return any(re.search(pattern, text) for pattern in feature_patterns)


def analyze_test_needs(data: dict) -> dict:
    """Main analysis function with sophisticated logic"""
    title = data['title']
    body = data.get('body', '')
    files = data['files']
    current_labels = data.get('labels', [])
    
    # Skip if already has no-tests-needed label
    if 'no-tests-needed' in current_labels:
        return {
            'needs_tests': False,
            'reason': 'no-tests-needed label present',
            'comment_message': None
        }
    
    # Filter Django core files
    django_files = [
        f for f in files 
        if f['filename'].startswith('django/') 
        and f['filename'].endswith('.py')
        and not f['filename'].startswith('django/tests/')
        and f['status'] in ['added', 'modified']
    ]
    
    # Filter test files
    test_files = [
        f for f in files 
        if f['filename'].startswith('tests/')
        and f['filename'].endswith('.py')
        and f['status'] in ['added', 'modified']
    ]
    
    # If no Django core changes, no tests needed
    if not django_files:
        return {
            'needs_tests': False,
            'reason': 'no Django core changes',
            'comment_message': None
        }
    
    # If tests already included, no need to flag
    if test_files:
        return {
            'needs_tests': False,
            'reason': 'tests already included',
            'comment_message': None
        }
    
    # Analyze each Django file for significance
    significant_changes = []
    trivial_changes = []
    
    for file_data in django_files:
        if CodeChangeAnalyzer.is_trivial_change(file_data):
            trivial_changes.append(file_data['filename'])
        else:
            change_analysis = {
                'filename': file_data['filename'],
                'has_new_functions': CodeChangeAnalyzer.has_new_functions_or_classes(file_data),
                'modifies_logic': CodeChangeAnalyzer.modifies_existing_logic(file_data),
                'expected_test_dirs': DjangoModuleMapper.get_expected_test_dirs(file_data['filename'])
            }
            significant_changes.append(change_analysis)
    
    # If all changes are trivial, no tests needed
    if not significant_changes:
        return {
            'needs_tests': False,
            'reason': 'all changes are trivial (docs, comments, whitespace)',
            'comment_message': None
        }
    
    # Determine if tests are needed based on change type
    is_bug_fix = CodeChangeAnalyzer.is_bug_fix(title, body)
    is_new_feature = CodeChangeAnalyzer.is_new_feature(title, body)
    has_new_code = any(c['has_new_functions'] for c in significant_changes)
    has_logic_changes = any(c['modifies_logic'] for c in significant_changes)
    
    needs_tests = (
        is_bug_fix or  # Bug fixes need regression tests
        is_new_feature or  # New features need tests
        has_new_code or  # New functions need tests
        has_logic_changes  # Logic changes need tests
    )
    
    if not needs_tests:
        return {
            'needs_tests': False,
            'reason': 'changes appear to be refactoring or style improvements',
            'comment_message': None
        }
    
    # Generate helpful comment
    reasons = []
    if is_bug_fix:
        reasons.append(" **Bug fix detected** - regression tests recommended")
    if is_new_feature:
        reasons.append(" **New feature detected** - feature tests recommended")
    if has_new_code:
        reasons.append(" **New functions/classes added** - unit tests recommended")
    if has_logic_changes:
        reasons.append(" **Existing logic modified** - tests should be updated")
    
    # Create test directory suggestions
    suggested_dirs = set()
    for change in significant_changes:
        suggested_dirs.update(change['expected_test_dirs'])
    
    file_list = '\n'.join(f"- `{c['filename']}`" for c in significant_changes)
    
    comment_message = f"""## Test Coverage Recommendation

This PR modifies Django core code but doesn't include tests.

**Modified Django files:**
{file_list}

**Why tests are recommended:**
{chr(10).join(f"- {reason}" for reason in reasons)}

**Suggested test locations:**
{chr(10).join(f"- `{dir_name}`" for dir_name in sorted(suggested_dirs))}

**If tests aren't needed:**
- Add the `no-tests-needed` label to dismiss this check
- Common exceptions: pure refactoring, documentation fixes, code style changes

*This analysis considers the type of changes made and Django's testing conventions.*"""
    
    return {
        'needs_tests': True,
        'reason': f"significant changes detected: {', '.join(reasons)}",
        'comment_message': comment_message,
        'analysis_details': {
            'django_files': len(django_files),
            'test_files': len(test_files),
            'significant_changes': len(significant_changes),
            'trivial_changes': len(trivial_changes),
            'is_bug_fix': is_bug_fix,
            'is_new_feature': is_new_feature,
            'has_new_code': has_new_code,
            'has_logic_changes': has_logic_changes
        }
    }


if __name__ == '__main__':
    try:
        data = json.loads(sys.stdin.read())
        result = analyze_test_needs(data)
        print(json.dumps(result, indent=2))
    except Exception as e:
        # Fallback result on error
        error_result = {
            'needs_tests': False,
            'reason': f'analysis error: {str(e)}',
            'comment_message': None
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)