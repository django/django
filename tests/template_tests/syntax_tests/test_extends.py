from django.template.base import Template
from django.test import SimpleTestCase

from .utils import render, setup


inheritance_templates = {
    'inheritance01': "1{% block first %}&{% endblock %}3{% block second %}_{% endblock %}",
    'inheritance02': "{% extends 'inheritance01' %}"
                     "{% block first %}2{% endblock %}{% block second %}4{% endblock %}",
    'inheritance03': "{% extends 'inheritance02' %}",
    'inheritance04': "{% extends 'inheritance01' %}",
    'inheritance05': "{% extends 'inheritance02' %}",
    'inheritance06': "{% extends foo %}",
    'inheritance07': "{% extends 'inheritance01' %}{% block second %}5{% endblock %}",
    'inheritance08': "{% extends 'inheritance02' %}{% block second %}5{% endblock %}",
    'inheritance09': "{% extends 'inheritance04' %}",
    'inheritance10': "{% extends 'inheritance04' %}      ",
    'inheritance11': "{% extends 'inheritance04' %}"
                     "{% block first %}2{% endblock %}{% block second %}4{% endblock %}",
    'inheritance12': "{% extends 'inheritance07' %}{% block first %}2{% endblock %}",
    'inheritance13': "{% extends 'inheritance02' %}"
                     "{% block first %}a{% endblock %}{% block second %}b{% endblock %}",
    'inheritance14': "{% extends 'inheritance01' %}{% block newblock %}NO DISPLAY{% endblock %}",
    'inheritance15': "{% extends 'inheritance01' %}"
                     "{% block first %}2{% block inner %}inner{% endblock %}{% endblock %}",
    'inheritance16': "{% extends 'inheritance15' %}{% block inner %}out{% endblock %}",
    'inheritance17': "{% load testtags %}{% block first %}1234{% endblock %}",
    'inheritance18': "{% load testtags %}{% echo this that theother %}5678",
    'inheritance19': "{% extends 'inheritance01' %}"
                     "{% block first %}{% load testtags %}{% echo 400 %}5678{% endblock %}",
    'inheritance20': "{% extends 'inheritance01' %}{% block first %}{{ block.super }}a{% endblock %}",
    'inheritance21': "{% extends 'inheritance02' %}{% block first %}{{ block.super }}a{% endblock %}",
    'inheritance22': "{% extends 'inheritance04' %}{% block first %}{{ block.super }}a{% endblock %}",
    'inheritance23': "{% extends 'inheritance20' %}{% block first %}{{ block.super }}b{% endblock %}",
    'inheritance24': "{% extends context_template %}"
                     "{% block first %}2{% endblock %}{% block second %}4{% endblock %}",
    'inheritance25': "{% extends context_template.1 %}"
                     "{% block first %}2{% endblock %}{% block second %}4{% endblock %}",
    'inheritance26': "no tags",
    'inheritance27': "{% extends 'inheritance26' %}",
    'inheritance 28': "{% block first %}!{% endblock %}",
    'inheritance29': "{% extends 'inheritance 28' %}",
    'inheritance30': "1{% if optional %}{% block opt %}2{% endblock %}{% endif %}3",
    'inheritance31': "{% extends 'inheritance30' %}{% block opt %}two{% endblock %}",
    'inheritance32': "{% extends 'inheritance30' %}{% block opt %}two{% endblock %}",
    'inheritance33': "1{% ifequal optional 1 %}{% block opt %}2{% endblock %}{% endifequal %}3",
    'inheritance34': "{% extends 'inheritance33' %}{% block opt %}two{% endblock %}",
    'inheritance35': "{% extends 'inheritance33' %}{% block opt %}two{% endblock %}",
    'inheritance36': "{% for n in numbers %}_{% block opt %}{{ n }}{% endblock %}{% endfor %}_",
    'inheritance37': "{% extends 'inheritance36' %}{% block opt %}X{% endblock %}",
    'inheritance38': "{% extends 'inheritance36' %}{% block opt %}X{% endblock %}",
    'inheritance39': "{% extends 'inheritance30' %}{% block opt %}new{{ block.super }}{% endblock %}",
    'inheritance40': "{% extends 'inheritance33' %}{% block opt %}new{{ block.super }}{% endblock %}",
    'inheritance41': "{% extends 'inheritance36' %}{% block opt %}new{{ block.super }}{% endblock %}",
    'inheritance42': "{% extends 'inheritance02'|cut:' ' %}",
}


class InheritanceTests(SimpleTestCase):

    @setup(inheritance_templates)
    def test_inheritance01(self):
        """
        Standard template with no inheritance
        """
        output = render('inheritance01')
        self.assertEqual(output, '1&3_')

    @setup(inheritance_templates)
    def test_inheritance02(self):
        """
        Standard two-level inheritance
        """
        output = render('inheritance02')
        self.assertEqual(output, '1234')

    @setup(inheritance_templates)
    def test_inheritance03(self):
        """
        Three-level with no redefinitions on third level
        """
        output = render('inheritance03')
        self.assertEqual(output, '1234')

    @setup(inheritance_templates)
    def test_inheritance04(self):
        """
        Two-level with no redefinitions on second level
        """
        output = render('inheritance04')
        self.assertEqual(output, '1&3_')

    @setup(inheritance_templates)
    def test_inheritance05(self):
        """
        Two-level with double quotes instead of single quotes
        """
        output = render('inheritance05')
        self.assertEqual(output, '1234')

    @setup(inheritance_templates)
    def test_inheritance06(self):
        """
        Three-level with variable parent-template name
        """
        output = render('inheritance06', {'foo': 'inheritance02'})
        self.assertEqual(output, '1234')

    @setup(inheritance_templates)
    def test_inheritance07(self):
        """
        Two-level with one block defined, one block not defined
        """
        output = render('inheritance07')
        self.assertEqual(output, '1&35')

    @setup(inheritance_templates)
    def test_inheritance08(self):
        """
        Three-level with one block defined on this level, two blocks
        defined next level
        """
        output = render('inheritance08')
        self.assertEqual(output, '1235')

    @setup(inheritance_templates)
    def test_inheritance09(self):
        """
        Three-level with second and third levels blank
        """
        output = render('inheritance09')
        self.assertEqual(output, '1&3_')

    @setup(inheritance_templates)
    def test_inheritance10(self):
        """
        Three-level with space NOT in a block -- should be ignored
        """
        output = render('inheritance10')
        self.assertEqual(output, '1&3_')

    @setup(inheritance_templates)
    def test_inheritance11(self):
        """
        Three-level with both blocks defined on this level, but none on
        second level
        """
        output = render('inheritance11')
        self.assertEqual(output, '1234')

    @setup(inheritance_templates)
    def test_inheritance12(self):
        """
        Three-level with this level providing one and second level
        providing the other
        """
        output = render('inheritance12')
        self.assertEqual(output, '1235')

    @setup(inheritance_templates)
    def test_inheritance13(self):
        """
        Three-level with this level overriding second level
        """
        output = render('inheritance13')
        self.assertEqual(output, '1a3b')

    @setup(inheritance_templates)
    def test_inheritance14(self):
        """
        A block defined only in a child template shouldn't be displayed
        """
        output = render('inheritance14')
        self.assertEqual(output, '1&3_')

    @setup(inheritance_templates)
    def test_inheritance15(self):
        """
        A block within another block
        """
        output = render('inheritance15')
        self.assertEqual(output, '12inner3_')

    @setup(inheritance_templates)
    def test_inheritance16(self):
        """
        A block within another block (level 2)
        """
        output = render('inheritance16')
        self.assertEqual(output, '12out3_')

    @setup(inheritance_templates)
    def test_inheritance17(self):
        """
        {% load %} tag (parent -- setup for exception04)
        """
        output = render('inheritance17')
        self.assertEqual(output, '1234')

    @setup(inheritance_templates)
    def test_inheritance18(self):
        """
        {% load %} tag (standard usage, without inheritance)
        """
        output = render('inheritance18')
        self.assertEqual(output, 'this that theother5678')

    @setup(inheritance_templates)
    def test_inheritance19(self):
        """
        {% load %} tag (within a child template)
        """
        output = render('inheritance19')
        self.assertEqual(output, '140056783_')

    @setup(inheritance_templates)
    def test_inheritance20(self):
        """
        Two-level inheritance with {{ block.super }}
        """
        output = render('inheritance20')
        self.assertEqual(output, '1&a3_')

    @setup(inheritance_templates)
    def test_inheritance21(self):
        """
        Three-level inheritance with {{ block.super }} from parent
        """
        output = render('inheritance21')
        self.assertEqual(output, '12a34')

    @setup(inheritance_templates)
    def test_inheritance22(self):
        """
        Three-level inheritance with {{ block.super }} from grandparent
        """
        output = render('inheritance22')
        self.assertEqual(output, '1&a3_')

    @setup(inheritance_templates)
    def test_inheritance23(self):
        """
        Three-level inheritance with {{ block.super }} from parent and
        grandparent
        """
        output = render('inheritance23')
        self.assertEqual(output, '1&ab3_')

    @setup(inheritance_templates)
    def test_inheritance24(self):
        """
        Inheritance from local context without use of template loader
        """
        output = render('inheritance24', {
            'context_template': Template("1{% block first %}_{% endblock %}3{% block second %}_{% endblock %}")
        })
        self.assertEqual(output, '1234')

    @setup(inheritance_templates)
    def test_inheritance25(self):
        """
        Inheritance from local context with variable parent template
        """
        output = render('inheritance25', {
            'context_template': [
                Template("Wrong"),
                Template("1{% block first %}_{% endblock %}3{% block second %}_{% endblock %}"),
            ],
        })
        self.assertEqual(output, '1234')

    @setup(inheritance_templates)
    def test_inheritance26(self):
        """
        Set up a base template to extend
        """
        output = render('inheritance26')
        self.assertEqual(output, 'no tags')

    @setup(inheritance_templates)
    def test_inheritance27(self):
        """
        Inheritance from a template that doesn't have any blocks
        """
        output = render('inheritance27')
        self.assertEqual(output, 'no tags')

    @setup(inheritance_templates)
    def test_inheritance_28(self):
        """
        Set up a base template with a space in it.
        """
        output = render('inheritance 28')
        self.assertEqual(output, '!')

    @setup(inheritance_templates)
    def test_inheritance29(self):
        """
        Inheritance from a template with a space in its name should work.
        """
        output = render('inheritance29')
        self.assertEqual(output, '!')

    @setup(inheritance_templates)
    def test_inheritance30(self):
        """
        Base template, putting block in a conditional {% if %} tag
        """
        output = render('inheritance30', {'optional': True})
        self.assertEqual(output, '123')

    # Inherit from a template with block wrapped in an {% if %} tag
    # (in parent), still gets overridden
    @setup(inheritance_templates)
    def test_inheritance31(self):
        output = render('inheritance31', {'optional': True})
        self.assertEqual(output, '1two3')

    @setup(inheritance_templates)
    def test_inheritance32(self):
        output = render('inheritance32')
        self.assertEqual(output, '13')

    @setup(inheritance_templates)
    def test_inheritance33(self):
        """
        Base template, putting block in a conditional {% ifequal %} tag
        """
        output = render('inheritance33', {'optional': 1})
        self.assertEqual(output, '123')

    @setup(inheritance_templates)
    def test_inheritance34(self):
        """
        Inherit from a template with block wrapped in an {% ifequal %} tag
        (in parent), still gets overridden
        """
        output = render('inheritance34', {'optional': 1})
        self.assertEqual(output, '1two3')

    @setup(inheritance_templates)
    def test_inheritance35(self):
        """
        Inherit from a template with block wrapped in an {% ifequal %} tag
        (in parent), still gets overridden
        """
        output = render('inheritance35', {'optional': 2})
        self.assertEqual(output, '13')

    @setup(inheritance_templates)
    def test_inheritance36(self):
        """
        Base template, putting block in a {% for %} tag
        """
        output = render('inheritance36', {'numbers': '123'})
        self.assertEqual(output, '_1_2_3_')

    @setup(inheritance_templates)
    def test_inheritance37(self):
        """
        Inherit from a template with block wrapped in an {% for %} tag
        (in parent), still gets overridden
        """
        output = render('inheritance37', {'numbers': '123'})
        self.assertEqual(output, '_X_X_X_')

    @setup(inheritance_templates)
    def test_inheritance38(self):
        """
        Inherit from a template with block wrapped in an {% for %} tag
        (in parent), still gets overridden
        """
        output = render('inheritance38')
        self.assertEqual(output, '_')

    # The super block will still be found.
    @setup(inheritance_templates)
    def test_inheritance39(self):
        output = render('inheritance39', {'optional': True})
        self.assertEqual(output, '1new23')

    @setup(inheritance_templates)
    def test_inheritance40(self):
        output = render('inheritance40', {'optional': 1})
        self.assertEqual(output, '1new23')

    @setup(inheritance_templates)
    def test_inheritance41(self):
        output = render('inheritance41', {'numbers': '123'})
        self.assertEqual(output, '_new1_new2_new3_')

    @setup(inheritance_templates)
    def test_inheritance42(self):
        """
        Expression starting and ending with a quote
        """
        output = render('inheritance42')
        self.assertEqual(output, '1234')
