import os

from asgiref.local import Local

from django.template import Context, Template, TemplateSyntaxError
from django.test import SimpleTestCase, override_settings
from django.utils import translation
from django.utils.safestring import mark_safe
from django.utils.translation import trans_real

from ...utils import setup
from .base import MultipleLocaleActivationTestCase, extended_locale_paths, here


class I18nBlockTransTagTests(SimpleTestCase):
    libraries = {'i18n': 'django.templatetags.i18n'}

    @setup({'i18n03': '{% load i18n %}{% blocktrans %}{{ anton }}{% endblocktrans %}'})
    def test_i18n03(self):
        """simple translation of a variable"""
        output = self.engine.render_to_string('i18n03', {'anton': 'Å'})
        self.assertEqual(output, 'Å')

    @setup({'i18n04': '{% load i18n %}{% blocktrans with berta=anton|lower %}{{ berta }}{% endblocktrans %}'})
    def test_i18n04(self):
        """simple translation of a variable and filter"""
        output = self.engine.render_to_string('i18n04', {'anton': 'Å'})
        self.assertEqual(output, 'å')

    @setup({'legacyi18n04': '{% load i18n %}'
                            '{% blocktrans with anton|lower as berta %}{{ berta }}{% endblocktrans %}'})
    def test_legacyi18n04(self):
        """simple translation of a variable and filter"""
        output = self.engine.render_to_string('legacyi18n04', {'anton': 'Å'})
        self.assertEqual(output, 'å')

    @setup({'i18n05': '{% load i18n %}{% blocktrans %}xxx{{ anton }}xxx{% endblocktrans %}'})
    def test_i18n05(self):
        """simple translation of a string with interpolation"""
        output = self.engine.render_to_string('i18n05', {'anton': 'yyy'})
        self.assertEqual(output, 'xxxyyyxxx')

    @setup({'i18n07': '{% load i18n %}'
                      '{% blocktrans count counter=number %}singular{% plural %}'
                      '{{ counter }} plural{% endblocktrans %}'})
    def test_i18n07(self):
        """translation of singular form"""
        output = self.engine.render_to_string('i18n07', {'number': 1})
        self.assertEqual(output, 'singular')

    @setup({'legacyi18n07': '{% load i18n %}'
                            '{% blocktrans count number as counter %}singular{% plural %}'
                            '{{ counter }} plural{% endblocktrans %}'})
    def test_legacyi18n07(self):
        """translation of singular form"""
        output = self.engine.render_to_string('legacyi18n07', {'number': 1})
        self.assertEqual(output, 'singular')

    @setup({'i18n08': '{% load i18n %}'
                      '{% blocktrans count number as counter %}singular{% plural %}'
                      '{{ counter }} plural{% endblocktrans %}'})
    def test_i18n08(self):
        """translation of plural form"""
        output = self.engine.render_to_string('i18n08', {'number': 2})
        self.assertEqual(output, '2 plural')

    @setup({'legacyi18n08': '{% load i18n %}'
                            '{% blocktrans count counter=number %}singular{% plural %}'
                            '{{ counter }} plural{% endblocktrans %}'})
    def test_legacyi18n08(self):
        """translation of plural form"""
        output = self.engine.render_to_string('legacyi18n08', {'number': 2})
        self.assertEqual(output, '2 plural')

    @setup({'i18n17': '{% load i18n %}'
                      '{% blocktrans with berta=anton|escape %}{{ berta }}{% endblocktrans %}'})
    def test_i18n17(self):
        """
        Escaping inside blocktrans and trans works as if it was directly in the
        template.
        """
        output = self.engine.render_to_string('i18n17', {'anton': 'α & β'})
        self.assertEqual(output, 'α &amp; β')

    @setup({'i18n18': '{% load i18n %}'
                      '{% blocktrans with berta=anton|force_escape %}{{ berta }}{% endblocktrans %}'})
    def test_i18n18(self):
        output = self.engine.render_to_string('i18n18', {'anton': 'α & β'})
        self.assertEqual(output, 'α &amp; β')

    @setup({'i18n19': '{% load i18n %}{% blocktrans %}{{ andrew }}{% endblocktrans %}'})
    def test_i18n19(self):
        output = self.engine.render_to_string('i18n19', {'andrew': 'a & b'})
        self.assertEqual(output, 'a &amp; b')

    @setup({'i18n21': '{% load i18n %}{% blocktrans %}{{ andrew }}{% endblocktrans %}'})
    def test_i18n21(self):
        output = self.engine.render_to_string('i18n21', {'andrew': mark_safe('a & b')})
        self.assertEqual(output, 'a & b')

    @setup({'legacyi18n17': '{% load i18n %}'
                            '{% blocktrans with anton|escape as berta %}{{ berta }}{% endblocktrans %}'})
    def test_legacyi18n17(self):
        output = self.engine.render_to_string('legacyi18n17', {'anton': 'α & β'})
        self.assertEqual(output, 'α &amp; β')

    @setup({'legacyi18n18': '{% load i18n %}'
                            '{% blocktrans with anton|force_escape as berta %}'
                            '{{ berta }}{% endblocktrans %}'})
    def test_legacyi18n18(self):
        output = self.engine.render_to_string('legacyi18n18', {'anton': 'α & β'})
        self.assertEqual(output, 'α &amp; β')

    @setup({'i18n26': '{% load i18n %}'
                      '{% blocktrans with extra_field=myextra_field count counter=number %}'
                      'singular {{ extra_field }}{% plural %}plural{% endblocktrans %}'})
    def test_i18n26(self):
        """
        translation of plural form with extra field in singular form (#13568)
        """
        output = self.engine.render_to_string('i18n26', {'myextra_field': 'test', 'number': 1})
        self.assertEqual(output, 'singular test')

    @setup({'legacyi18n26': '{% load i18n %}'
                            '{% blocktrans with myextra_field as extra_field count number as counter %}'
                            'singular {{ extra_field }}{% plural %}plural{% endblocktrans %}'})
    def test_legacyi18n26(self):
        output = self.engine.render_to_string('legacyi18n26', {'myextra_field': 'test', 'number': 1})
        self.assertEqual(output, 'singular test')

    @setup({'i18n27': '{% load i18n %}{% blocktrans count counter=number %}'
                      '{{ counter }} result{% plural %}{{ counter }} results'
                      '{% endblocktrans %}'})
    def test_i18n27(self):
        """translation of singular form in Russian (#14126)"""
        with translation.override('ru'):
            output = self.engine.render_to_string('i18n27', {'number': 1})
        self.assertEqual(output, '1 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442')

    @setup({'legacyi18n27': '{% load i18n %}'
                            '{% blocktrans count number as counter %}{{ counter }} result'
                            '{% plural %}{{ counter }} results{% endblocktrans %}'})
    def test_legacyi18n27(self):
        with translation.override('ru'):
            output = self.engine.render_to_string('legacyi18n27', {'number': 1})
        self.assertEqual(output, '1 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442')

    @setup({'i18n28': '{% load i18n %}'
                      '{% blocktrans with a=anton b=berta %}{{ a }} + {{ b }}{% endblocktrans %}'})
    def test_i18n28(self):
        """simple translation of multiple variables"""
        output = self.engine.render_to_string('i18n28', {'anton': 'α', 'berta': 'β'})
        self.assertEqual(output, 'α + β')

    @setup({'legacyi18n28': '{% load i18n %}'
                            '{% blocktrans with anton as a and berta as b %}'
                            '{{ a }} + {{ b }}{% endblocktrans %}'})
    def test_legacyi18n28(self):
        output = self.engine.render_to_string('legacyi18n28', {'anton': 'α', 'berta': 'β'})
        self.assertEqual(output, 'α + β')

    # blocktrans handling of variables which are not in the context.
    # this should work as if blocktrans was not there (#19915)
    @setup({'i18n34': '{% load i18n %}{% blocktrans %}{{ missing }}{% endblocktrans %}'})
    def test_i18n34(self):
        output = self.engine.render_to_string('i18n34')
        if self.engine.string_if_invalid:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    @setup({'i18n34_2': '{% load i18n %}{% blocktrans with a=\'α\' %}{{ missing }}{% endblocktrans %}'})
    def test_i18n34_2(self):
        output = self.engine.render_to_string('i18n34_2')
        if self.engine.string_if_invalid:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    @setup({'i18n34_3': '{% load i18n %}{% blocktrans with a=anton %}{{ missing }}{% endblocktrans %}'})
    def test_i18n34_3(self):
        output = self.engine.render_to_string(
            'i18n34_3', {'anton': '\xce\xb1'})
        if self.engine.string_if_invalid:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    @setup({'i18n37': '{% load i18n %}'
                      '{% trans "Page not found" as page_not_found %}'
                      '{% blocktrans %}Error: {{ page_not_found }}{% endblocktrans %}'})
    def test_i18n37(self):
        with translation.override('de'):
            output = self.engine.render_to_string('i18n37')
        self.assertEqual(output, 'Error: Seite nicht gefunden')

    # blocktrans tag with asvar
    @setup({'i18n39': '{% load i18n %}'
                      '{% blocktrans asvar page_not_found %}Page not found{% endblocktrans %}'
                      '>{{ page_not_found }}<'})
    def test_i18n39(self):
        with translation.override('de'):
            output = self.engine.render_to_string('i18n39')
        self.assertEqual(output, '>Seite nicht gefunden<')

    @setup({'i18n40': '{% load i18n %}'
                      '{% trans "Page not found" as pg_404 %}'
                      '{% blocktrans with page_not_found=pg_404 asvar output %}'
                      'Error: {{ page_not_found }}'
                      '{% endblocktrans %}'})
    def test_i18n40(self):
        output = self.engine.render_to_string('i18n40')
        self.assertEqual(output, '')

    @setup({'i18n41': '{% load i18n %}'
                      '{% trans "Page not found" as pg_404 %}'
                      '{% blocktrans with page_not_found=pg_404 asvar output %}'
                      'Error: {{ page_not_found }}'
                      '{% endblocktrans %}'
                      '>{{ output }}<'})
    def test_i18n41(self):
        with translation.override('de'):
            output = self.engine.render_to_string('i18n41')
        self.assertEqual(output, '>Error: Seite nicht gefunden<')

    @setup({'template': '{% load i18n %}{% blocktrans asvar %}Yes{% endblocktrans %}'})
    def test_blocktrans_syntax_error_missing_assignment(self):
        msg = "No argument provided to the 'blocktrans' tag for the asvar option."
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('template')

    @setup({'template': '{% load i18n %}{% blocktrans %}%s{% endblocktrans %}'})
    def test_blocktrans_tag_using_a_string_that_looks_like_str_fmt(self):
        output = self.engine.render_to_string('template')
        self.assertEqual(output, '%s')

    @setup({'template': '{% load i18n %}{% blocktrans %}{% block b %} {% endblock %}{% endblocktrans %}'})
    def test_with_block(self):
        msg = "'blocktrans' doesn't allow other block tags (seen 'block b') inside it"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('template')

    @setup({'template': '{% load i18n %}{% blocktrans %}{% for b in [1, 2, 3] %} {% endfor %}{% endblocktrans %}'})
    def test_with_for(self):
        msg = "'blocktrans' doesn't allow other block tags (seen 'for b in [1, 2, 3]') inside it"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('template')

    @setup({'template': '{% load i18n %}{% blocktrans with foo=bar with %}{{ foo }}{% endblocktrans %}'})
    def test_variable_twice(self):
        with self.assertRaisesMessage(TemplateSyntaxError, "The 'with' option was specified more than once"):
            self.engine.render_to_string('template', {'foo': 'bar'})

    @setup({'template': '{% load i18n %}{% blocktrans with %}{% endblocktrans %}'})
    def test_no_args_with(self):
        msg = '"with" in \'blocktrans\' tag needs at least one keyword argument.'
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('template')

    @setup({'template': '{% load i18n %}{% blocktrans count a %}{% endblocktrans %}'})
    def test_count(self):
        msg = '"count" in \'blocktrans\' tag expected exactly one keyword argument.'
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('template', {'a': [1, 2, 3]})

    @setup({'template': (
        '{% load i18n %}{% blocktrans count count=var|length %}'
        'There is {{ count }} object. {% block a %} {% endblock %}'
        '{% endblocktrans %}'
    )})
    def test_plural_bad_syntax(self):
        msg = "'blocktrans' doesn't allow other block tags inside it"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('template', {'var': [1, 2, 3]})


class TranslationBlockTransTagTests(SimpleTestCase):

    @override_settings(LOCALE_PATHS=extended_locale_paths)
    def test_template_tags_pgettext(self):
        """{% blocktrans %} takes message contexts into account (#14806)."""
        trans_real._active = Local()
        trans_real._translations = {}
        with translation.override('de'):
            # Nonexistent context
            t = Template('{% load i18n %}{% blocktrans context "nonexistent" %}May{% endblocktrans %}')
            rendered = t.render(Context())
            self.assertEqual(rendered, 'May')

            # Existing context...  using a literal
            t = Template('{% load i18n %}{% blocktrans context "month name" %}May{% endblocktrans %}')
            rendered = t.render(Context())
            self.assertEqual(rendered, 'Mai')
            t = Template('{% load i18n %}{% blocktrans context "verb" %}May{% endblocktrans %}')
            rendered = t.render(Context())
            self.assertEqual(rendered, 'Kann')

            # Using a variable
            t = Template('{% load i18n %}{% blocktrans context message_context %}May{% endblocktrans %}')
            rendered = t.render(Context({'message_context': 'month name'}))
            self.assertEqual(rendered, 'Mai')
            t = Template('{% load i18n %}{% blocktrans context message_context %}May{% endblocktrans %}')
            rendered = t.render(Context({'message_context': 'verb'}))
            self.assertEqual(rendered, 'Kann')

            # Using a filter
            t = Template('{% load i18n %}{% blocktrans context message_context|lower %}May{% endblocktrans %}')
            rendered = t.render(Context({'message_context': 'MONTH NAME'}))
            self.assertEqual(rendered, 'Mai')
            t = Template('{% load i18n %}{% blocktrans context message_context|lower %}May{% endblocktrans %}')
            rendered = t.render(Context({'message_context': 'VERB'}))
            self.assertEqual(rendered, 'Kann')

            # Using 'count'
            t = Template(
                '{% load i18n %}{% blocktrans count number=1 context "super search" %}'
                '{{ number }} super result{% plural %}{{ number }} super results{% endblocktrans %}'
            )
            rendered = t.render(Context())
            self.assertEqual(rendered, '1 Super-Ergebnis')
            t = Template(
                '{% load i18n %}{% blocktrans count number=2 context "super search" %}{{ number }}'
                ' super result{% plural %}{{ number }} super results{% endblocktrans %}'
            )
            rendered = t.render(Context())
            self.assertEqual(rendered, '2 Super-Ergebnisse')
            t = Template(
                '{% load i18n %}{% blocktrans context "other super search" count number=1 %}'
                '{{ number }} super result{% plural %}{{ number }} super results{% endblocktrans %}'
            )
            rendered = t.render(Context())
            self.assertEqual(rendered, '1 anderen Super-Ergebnis')
            t = Template(
                '{% load i18n %}{% blocktrans context "other super search" count number=2 %}'
                '{{ number }} super result{% plural %}{{ number }} super results{% endblocktrans %}'
            )
            rendered = t.render(Context())
            self.assertEqual(rendered, '2 andere Super-Ergebnisse')

            # Using 'with'
            t = Template(
                '{% load i18n %}{% blocktrans with num_comments=5 context "comment count" %}'
                'There are {{ num_comments }} comments{% endblocktrans %}'
            )
            rendered = t.render(Context())
            self.assertEqual(rendered, 'Es gibt 5 Kommentare')
            t = Template(
                '{% load i18n %}{% blocktrans with num_comments=5 context "other comment count" %}'
                'There are {{ num_comments }} comments{% endblocktrans %}'
            )
            rendered = t.render(Context())
            self.assertEqual(rendered, 'Andere: Es gibt 5 Kommentare')

            # Using trimmed
            t = Template(
                '{% load i18n %}{% blocktrans trimmed %}\n\nThere\n\t are 5  '
                '\n\n   comments\n{% endblocktrans %}'
            )
            rendered = t.render(Context())
            self.assertEqual(rendered, 'There are 5 comments')
            t = Template(
                '{% load i18n %}{% blocktrans with num_comments=5 context "comment count" trimmed %}\n\n'
                'There are  \t\n  \t {{ num_comments }} comments\n\n{% endblocktrans %}'
            )
            rendered = t.render(Context())
            self.assertEqual(rendered, 'Es gibt 5 Kommentare')
            t = Template(
                '{% load i18n %}{% blocktrans context "other super search" count number=2 trimmed %}\n'
                '{{ number }} super \n result{% plural %}{{ number }} super results{% endblocktrans %}'
            )
            rendered = t.render(Context())
            self.assertEqual(rendered, '2 andere Super-Ergebnisse')

            # Misuses
            msg = "Unknown argument for 'blocktrans' tag: %r."
            with self.assertRaisesMessage(TemplateSyntaxError, msg % 'month="May"'):
                Template('{% load i18n %}{% blocktrans context with month="May" %}{{ month }}{% endblocktrans %}')
            msg = '"context" in %r tag expected exactly one argument.' % 'blocktrans'
            with self.assertRaisesMessage(TemplateSyntaxError, msg):
                Template('{% load i18n %}{% blocktrans context %}{% endblocktrans %}')
            with self.assertRaisesMessage(TemplateSyntaxError, msg):
                Template(
                    '{% load i18n %}{% blocktrans count number=2 context %}'
                    '{{ number }} super result{% plural %}{{ number }}'
                    ' super results{% endblocktrans %}'
                )

    @override_settings(LOCALE_PATHS=[os.path.join(here, 'other', 'locale')])
    def test_bad_placeholder_1(self):
        """
        Error in translation file should not crash template rendering (#16516).
        (%(person)s is translated as %(personne)s in fr.po).
        """
        with translation.override('fr'):
            t = Template('{% load i18n %}{% blocktrans %}My name is {{ person }}.{% endblocktrans %}')
            rendered = t.render(Context({'person': 'James'}))
            self.assertEqual(rendered, 'My name is James.')

    @override_settings(LOCALE_PATHS=[os.path.join(here, 'other', 'locale')])
    def test_bad_placeholder_2(self):
        """
        Error in translation file should not crash template rendering (#18393).
        (%(person) misses a 's' in fr.po, causing the string formatting to fail)
        .
        """
        with translation.override('fr'):
            t = Template('{% load i18n %}{% blocktrans %}My other name is {{ person }}.{% endblocktrans %}')
            rendered = t.render(Context({'person': 'James'}))
            self.assertEqual(rendered, 'My other name is James.')


class MultipleLocaleActivationBlockTransTests(MultipleLocaleActivationTestCase):

    def test_single_locale_activation(self):
        """
        Simple baseline behavior with one locale for all the supported i18n
        constructs.
        """
        with translation.override('fr'):
            self.assertEqual(
                Template("{% load i18n %}{% blocktrans %}Yes{% endblocktrans %}").render(Context({})),
                'Oui'
            )

    def test_multiple_locale_btrans(self):
        with translation.override('de'):
            t = Template("{% load i18n %}{% blocktrans %}No{% endblocktrans %}")
        with translation.override(self._old_language), translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'Nee')

    def test_multiple_locale_deactivate_btrans(self):
        with translation.override('de', deactivate=True):
            t = Template("{% load i18n %}{% blocktrans %}No{% endblocktrans %}")
        with translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'Nee')

    def test_multiple_locale_direct_switch_btrans(self):
        with translation.override('de'):
            t = Template("{% load i18n %}{% blocktrans %}No{% endblocktrans %}")
        with translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'Nee')


class MiscTests(SimpleTestCase):

    @override_settings(LOCALE_PATHS=extended_locale_paths)
    def test_percent_in_translatable_block(self):
        t_sing = Template("{% load i18n %}{% blocktrans %}The result was {{ percent }}%{% endblocktrans %}")
        t_plur = Template(
            "{% load i18n %}{% blocktrans count num as number %}"
            "{{ percent }}% represents {{ num }} object{% plural %}"
            "{{ percent }}% represents {{ num }} objects{% endblocktrans %}"
        )
        with translation.override('de'):
            self.assertEqual(t_sing.render(Context({'percent': 42})), 'Das Ergebnis war 42%')
            self.assertEqual(t_plur.render(Context({'percent': 42, 'num': 1})), '42% stellt 1 Objekt dar')
            self.assertEqual(t_plur.render(Context({'percent': 42, 'num': 4})), '42% stellt 4 Objekte dar')

    @override_settings(LOCALE_PATHS=extended_locale_paths)
    def test_percent_formatting_in_blocktrans(self):
        """
        Python's %-formatting is properly escaped in blocktrans, singular, or
        plural.
        """
        t_sing = Template("{% load i18n %}{% blocktrans %}There are %(num_comments)s comments{% endblocktrans %}")
        t_plur = Template(
            "{% load i18n %}{% blocktrans count num as number %}"
            "%(percent)s% represents {{ num }} object{% plural %}"
            "%(percent)s% represents {{ num }} objects{% endblocktrans %}"
        )
        with translation.override('de'):
            # Strings won't get translated as they don't match after escaping %
            self.assertEqual(t_sing.render(Context({'num_comments': 42})), 'There are %(num_comments)s comments')
            self.assertEqual(t_plur.render(Context({'percent': 42, 'num': 1})), '%(percent)s% represents 1 object')
            self.assertEqual(t_plur.render(Context({'percent': 42, 'num': 4})), '%(percent)s% represents 4 objects')
