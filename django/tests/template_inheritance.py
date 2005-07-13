from django.core import template, template_loader

# SYNTAX --
# 'template_name': ('template contents', 'context dict', 'expected string output' or Exception class)
TEMPLATE_TESTS = {
    # Standard template with no inheritance
    'test01': ("1{% block first %}_{% endblock %}3{% block second %}_{% endblock %}", {}, '1_3_'),

    # Standard two-level inheritance
    'test02': ("{% extends 'test01' %}{% block first %}2{% endblock %}{% block second %}4{% endblock %}", {}, '1234'),

    # Three-level with no redefinitions on third level
    'test03': ("{% extends 'test02' %}", {}, '1234'),

    # Two-level with no redefinitions on second level
    'test04': ("{% extends 'test01' %}", {}, '1_3_'),

    # Two-level with double quotes instead of single quotes
    'test05': ('{% extends "test02" %}', {}, '1234'),

    # Three-level with variable parent-template name
    'test06': ("{% extends foo %}", {'foo': 'test02'}, '1234'),

    # Two-level with one block defined, one block not defined
    'test07': ("{% extends 'test01' %}{% block second %}5{% endblock %}", {}, '1_35'),

    # Three-level with one block defined on this level, two blocks defined next level
    'test08': ("{% extends 'test02' %}{% block second %}5{% endblock %}", {}, '1235'),

    # Three-level with second and third levels blank
    'test09': ("{% extends 'test04' %}", {}, '1_3_'),

    # Three-level with space NOT in a block -- should be ignored
    'test10': ("{% extends 'test04' %}      ", {}, '1_3_'),

    # Three-level with both blocks defined on this level, but none on second level
    'test11': ("{% extends 'test04' %}{% block first %}2{% endblock %}{% block second %}4{% endblock %}", {}, '1234'),

    # Three-level with this level providing one and second level providing the other
    'test12': ("{% extends 'test07' %}{% block first %}2{% endblock %}", {}, '1235'),

    # Three-level with this level overriding second level
    'test13': ("{% extends 'test02' %}{% block first %}a{% endblock %}{% block second %}b{% endblock %}", {}, '1a3b'),

    # A block defined only in a child template shouldn't be displayed
    'test14': ("{% extends 'test01' %}{% block newblock %}NO DISPLAY{% endblock %}", {}, '1_3_'),

    # A block within another block
    'test15': ("{% extends 'test01' %}{% block first %}2{% block inner %}inner{% endblock %}{% endblock %}", {}, '12inner3_'),

    # A block within another block (level 2)
    'test16': ("{% extends 'test15' %}{% block inner %}out{% endblock %}", {}, '12out3_'),

    # {% load %} tag (parent -- setup for test-exception04)
    'test17': ("{% load polls.polls %}{% block first %}1234{% endblock %}", {}, '1234'),

    # {% load %} tag (standard usage, without inheritance)
    'test18': ("{% load polls.polls %}{% voteratio choice poll 400 %}5678", {}, '05678'),

    # {% load %} tag (within a child template)
    'test19': ("{% extends 'test01' %}{% block first %}{% load polls.polls %}{% voteratio choice poll 400 %}5678{% endblock %}", {}, '1056783_'),

    # Raise exception for invalid template name
    'test-exception01': ("{% extends 'nonexistent' %}", {}, template.TemplateSyntaxError),

    # Raise exception for invalid template name (in variable)
    'test-exception02': ("{% extends nonexistent %}", {}, template.TemplateSyntaxError),

    # Raise exception for extra {% extends %} tags
    'test-exception03': ("{% extends 'test01' %}{% block first %}2{% endblock %}{% extends 'test16' %}", {}, template.TemplateSyntaxError),

    # Raise exception for custom tags used in child with {% load %} tag in parent, not in child
    'test-exception04': ("{% extends 'test17' %}{% block first %}{% votegraph choice poll 400 %}5678{% endblock %}", {}, template.TemplateSyntaxError),
}

# This replaces the standard template_loader.
def test_template_loader(template_name):
    try:
        return TEMPLATE_TESTS[template_name][0]
    except KeyError:
        raise template.TemplateDoesNotExist, template_name
template_loader.load_template_source = test_template_loader

def run_tests():
    tests = TEMPLATE_TESTS.items()
    tests.sort()
    for name, vals in tests:
        try:
            output = template_loader.get_template(name).render(template.Context(vals[1]))
        except Exception, e:
            if e.__class__ == vals[2]:
                print "%s -- Passed" % name
            else:
                print "%s -- FAILED. Got %s, exception: %s" % (name, e.__class__, e)
            continue
        if output == vals[2]:
            print "%s -- Passed" % name
        else:
            print "%s -- FAILED. Expected %r, got %r" % (name, vals[2], output)

if __name__ == "__main__":
    run_tests()
