# coding: utf-8
from django.core.urlresolvers import NoReverseMatch
from django.template import TemplateSyntaxError
from django.test import SimpleTestCase, ignore_warnings, override_settings
from django.utils.deprecation import RemovedInDjango110Warning

from ..utils import setup


@override_settings(ROOT_URLCONF='template_tests.urls')
class UrlTagTests(SimpleTestCase):

    # Successes
    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url01': '{% url "template_tests.views.client" client.id %}'})
    def test_url01(self):
        output = self.engine.render_to_string('url01', {'client': {'id': 1}})
        self.assertEqual(output, '/client/1/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url02': '{% url "template_tests.views.client_action" id=client.id action="update" %}'})
    def test_url02(self):
        output = self.engine.render_to_string('url02', {'client': {'id': 1}})
        self.assertEqual(output, '/client/1/update/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url02a': '{% url "template_tests.views.client_action" client.id "update" %}'})
    def test_url02a(self):
        output = self.engine.render_to_string('url02a', {'client': {'id': 1}})
        self.assertEqual(output, '/client/1/update/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url02b': "{% url 'template_tests.views.client_action' id=client.id action='update' %}"})
    def test_url02b(self):
        output = self.engine.render_to_string('url02b', {'client': {'id': 1}})
        self.assertEqual(output, '/client/1/update/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url02c': "{% url 'template_tests.views.client_action' client.id 'update' %}"})
    def test_url02c(self):
        output = self.engine.render_to_string('url02c', {'client': {'id': 1}})
        self.assertEqual(output, '/client/1/update/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url03': '{% url "template_tests.views.index" %}'})
    def test_url03(self):
        output = self.engine.render_to_string('url03')
        self.assertEqual(output, '/')

    @setup({'url04': '{% url "named.client" client.id %}'})
    def test_url04(self):
        output = self.engine.render_to_string('url04', {'client': {'id': 1}})
        self.assertEqual(output, '/named-client/1/')

    @setup({'url05': '{% url "метка_оператора" v %}'})
    def test_url05(self):
        output = self.engine.render_to_string('url05', {'v': 'Ω'})
        self.assertEqual(output, '/%D0%AE%D0%BD%D0%B8%D0%BA%D0%BE%D0%B4/%CE%A9/')

    @setup({'url06': '{% url "метка_оператора_2" tag=v %}'})
    def test_url06(self):
        output = self.engine.render_to_string('url06', {'v': 'Ω'})
        self.assertEqual(output, '/%D0%AE%D0%BD%D0%B8%D0%BA%D0%BE%D0%B4/%CE%A9/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url07': '{% url "template_tests.views.client2" tag=v %}'})
    def test_url07(self):
        output = self.engine.render_to_string('url07', {'v': 'Ω'})
        self.assertEqual(output, '/%D0%AE%D0%BD%D0%B8%D0%BA%D0%BE%D0%B4/%CE%A9/')

    @setup({'url08': '{% url "метка_оператора" v %}'})
    def test_url08(self):
        output = self.engine.render_to_string('url08', {'v': 'Ω'})
        self.assertEqual(output, '/%D0%AE%D0%BD%D0%B8%D0%BA%D0%BE%D0%B4/%CE%A9/')

    @setup({'url09': '{% url "метка_оператора_2" tag=v %}'})
    def test_url09(self):
        output = self.engine.render_to_string('url09', {'v': 'Ω'})
        self.assertEqual(output, '/%D0%AE%D0%BD%D0%B8%D0%BA%D0%BE%D0%B4/%CE%A9/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url10': '{% url "template_tests.views.client_action" id=client.id action="two words" %}'})
    def test_url10(self):
        output = self.engine.render_to_string('url10', {'client': {'id': 1}})
        self.assertEqual(output, '/client/1/two%20words/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url11': '{% url "template_tests.views.client_action" id=client.id action="==" %}'})
    def test_url11(self):
        output = self.engine.render_to_string('url11', {'client': {'id': 1}})
        self.assertEqual(output, '/client/1/==/')

    @setup({'url12': '{% url "template_tests.views.client_action" '
                     'id=client.id action="!$&\'()*+,;=~:@," %}'})
    @ignore_warnings(category=RemovedInDjango110Warning)
    def test_url12(self):
        output = self.engine.render_to_string('url12', {'client': {'id': 1}})
        self.assertEqual(output, '/client/1/!$&\'()*+,;=~:@,/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url13': '{% url "template_tests.views.client_action" '
                     'id=client.id action=arg|join:"-" %}'})
    def test_url13(self):
        output = self.engine.render_to_string('url13', {'client': {'id': 1}, 'arg': ['a', 'b']})
        self.assertEqual(output, '/client/1/a-b/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url14': '{% url "template_tests.views.client_action" client.id arg|join:"-" %}'})
    def test_url14(self):
        output = self.engine.render_to_string('url14', {'client': {'id': 1}, 'arg': ['a', 'b']})
        self.assertEqual(output, '/client/1/a-b/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url15': '{% url "template_tests.views.client_action" 12 "test" %}'})
    def test_url15(self):
        output = self.engine.render_to_string('url15')
        self.assertEqual(output, '/client/12/test/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url18': '{% url "template_tests.views.client" "1,2" %}'})
    def test_url18(self):
        output = self.engine.render_to_string('url18')
        self.assertEqual(output, '/client/1,2/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url19': '{% url named_url client.id %}'})
    def test_url19(self):
        output = self.engine.render_to_string('url19', {'client': {'id': 1}, 'named_url': 'template_tests.views.client'})
        self.assertEqual(output, '/client/1/')

    @setup({'url20': '{% url url_name_in_var client.id %}'})
    def test_url20(self):
        output = self.engine.render_to_string('url20', {'client': {'id': 1}, 'url_name_in_var': 'named.client'})
        self.assertEqual(output, '/named-client/1/')

    # Failures
    @setup({'url-fail01': '{% url %}'})
    def test_url_fail01(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('url-fail01')

    @setup({'url-fail02': '{% url "no_such_view" %}'})
    def test_url_fail02(self):
        with self.assertRaises(NoReverseMatch):
            self.engine.render_to_string('url-fail02')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url-fail03': '{% url "template_tests.views.client" %}'})
    def test_url_fail03(self):
        with self.assertRaises(NoReverseMatch):
            self.engine.render_to_string('url-fail03')

    @setup({'url-fail04': '{% url "view" id, %}'})
    def test_url_fail04(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('url-fail04')

    @setup({'url-fail05': '{% url "view" id= %}'})
    def test_url_fail05(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('url-fail05')

    @setup({'url-fail06': '{% url "view" a.id=id %}'})
    def test_url_fail06(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('url-fail06')

    @setup({'url-fail07': '{% url "view" a.id!id %}'})
    def test_url_fail07(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('url-fail07')

    @setup({'url-fail08': '{% url "view" id="unterminatedstring %}'})
    def test_url_fail08(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('url-fail08')

    @setup({'url-fail09': '{% url "view" id=", %}'})
    def test_url_fail09(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('url-fail09')

    @setup({'url-fail11': '{% url named_url %}'})
    def test_url_fail11(self):
        with self.assertRaises(NoReverseMatch):
            self.engine.render_to_string('url-fail11')

    @setup({'url-fail12': '{% url named_url %}'})
    def test_url_fail12(self):
        with self.assertRaises(NoReverseMatch):
            self.engine.render_to_string('url-fail12', {'named_url': 'no_such_view'})

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url-fail13': '{% url named_url %}'})
    def test_url_fail13(self):
        with self.assertRaises(NoReverseMatch):
            self.engine.render_to_string('url-fail13', {'named_url': 'template_tests.views.client'})

    @setup({'url-fail14': '{% url named_url id, %}'})
    def test_url_fail14(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string('url-fail14', {'named_url': 'view'})

    @setup({'url-fail15': '{% url named_url id= %}'})
    def test_url_fail15(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string('url-fail15', {'named_url': 'view'})

    @setup({'url-fail16': '{% url named_url a.id=id %}'})
    def test_url_fail16(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string('url-fail16', {'named_url': 'view'})

    @setup({'url-fail17': '{% url named_url a.id!id %}'})
    def test_url_fail17(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string('url-fail17', {'named_url': 'view'})

    @setup({'url-fail18': '{% url named_url id="unterminatedstring %}'})
    def test_url_fail18(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string('url-fail18', {'named_url': 'view'})

    @setup({'url-fail19': '{% url named_url id=", %}'})
    def test_url_fail19(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string('url-fail19', {'named_url': 'view'})

    # {% url ... as var %}
    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url-asvar01': '{% url "template_tests.views.index" as url %}'})
    def test_url_asvar01(self):
        output = self.engine.render_to_string('url-asvar01')
        self.assertEqual(output, '')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'url-asvar02': '{% url "template_tests.views.index" as url %}{{ url }}'})
    def test_url_asvar02(self):
        output = self.engine.render_to_string('url-asvar02')
        self.assertEqual(output, '/')

    @setup({'url-asvar03': '{% url "no_such_view" as url %}{{ url }}'})
    def test_url_asvar03(self):
        output = self.engine.render_to_string('url-asvar03')
        self.assertEqual(output, '')
