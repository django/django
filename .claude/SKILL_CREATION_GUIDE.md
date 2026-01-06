# Claude Skills Creation Guide for Django

This document outlines best practices for creating effective Claude Skills.

## Core Quality Checklist

### Description Requirements
- [ ] Specific and includes key terms
- [ ] Describes both **what** the Skill does AND **when** to use it
- [ ] Uses consistent terminology throughout

### Size and Structure
- [ ] SKILL.md body under 500 lines
- [ ] Additional details in separate reference files (if needed)
- [ ] References are one level deep from SKILL.md
- [ ] Progressive disclosure used appropriately
- [ ] Reference files >100 lines have table of contents

### Content Quality
- [ ] No time-sensitive information (or in "old patterns" section)
- [ ] Examples are concrete, not abstract
- [ ] Workflows have clear steps

## Scripts and Code Quality

### Script Requirements
- [ ] Scripts solve problems rather than punt to Claude
- [ ] Error handling is explicit and helpful
- [ ] No "voodoo constants" (all values justified)
- [ ] Required packages listed and verified as available
- [ ] Scripts have clear documentation
- [ ] All paths use forward slashes (no Windows-style)
- [ ] Validation/verification steps for critical operations
- [ ] Feedback loops included for quality-critical tasks

## Structure Pattern

```
skill-name/
├── SKILL.md              # Overview, points to reference files
└── reference/
    ├── topic-a.md        # Specific topic details
    ├── topic-b.md        # Another topic
    └── examples/         # Concrete examples
        └── example-1.py
```

## Key Patterns

### Plan-Validate-Execute
For complex tasks, create verifiable intermediate outputs:
1. **Analyze** - Understand the task
2. **Create plan file** - Structured format (e.g., JSON)
3. **Validate plan** - Script checks for errors
4. **Execute** - Apply changes
5. **Verify** - Confirm results

### Progressive Disclosure
- SKILL.md contains overview and quick-start
- Detailed information in separate reference files
- Claude reads full files when needed

### Avoid Anti-patterns
- Deeply nested references (Claude may partially read)
- Time-sensitive information without versioning
- Abstract examples instead of concrete ones
- Windows-style paths
- Magic numbers without explanation

## Django-Specific Considerations

When creating Django skills:
1. Follow Django's coding style conventions
2. Reference Django's official patterns
3. Include migration safety considerations
4. Consider backwards compatibility
5. Test with Django's test framework patterns
6. Handle database operations properly
7. Follow security best practices (CSRF, XSS, SQL injection)
