import os

from django.template import Context, Engine, TemplateSyntaxError
from django.test import SimpleTestCase

from .utils import ROOT

RELATIVE = os.path.join(ROOT, 'relative_templates')


class ExtendsRelativeBehaviorTests(SimpleTestCase):

    def test_normal_extend(self):
        engine = Engine(dirs=[RELATIVE])
        template = engine.get_template('one.html')
        output = template.render(Context({}))
        self.assertEqual(output.strip(), 'three two one')

    def test_dir1_extend(self):
        engine = Engine(dirs=[RELATIVE])
        template = engine.get_template('dir1/one.html')
        output = template.render(Context({}))
        self.assertEqual(output.strip(), 'three two one dir1 one')

    def test_dir2_extend(self):
        engine = Engine(dirs=[RELATIVE])
        template = engine.get_template('dir1/dir2/one.html')
        output = template.render(Context({}))
        self.assertEqual(output.strip(), 'three two one dir2 one')

    def test_extend_error(self):
        engine = Engine(dirs=[RELATIVE])
        msg = "Relative name '\"./../two.html\"' have more parent folders, " \
              "then given template name 'error_extends.html'"

        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            engine.render_to_string('error_extends.html')


class IncludeRelativeBehaviorTests(SimpleTestCase):

    def test_normal_include(self):
        engine = Engine(dirs=[RELATIVE])
        template = engine.get_template('dir1/dir2/inc2.html')
        output = template.render(Context({}))
        self.assertEqual(output.strip(), 'dir2 include')

    def test_dir2_include(self):
        engine = Engine(dirs=[RELATIVE])
        template = engine.get_template('dir1/dir2/inc1.html')
        output = template.render(Context({}))
        self.assertEqual(output.strip(), 'three')

    def test_include_error(self):
        engine = Engine(dirs=[RELATIVE])
        msg = "Relative name '\"./../three.html\"' have more parent folders, " \
              "then given template name 'error_include.html'"

        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            engine.render_to_string('error_include.html')


class ExtendsMixedBehaviorTests(SimpleTestCase):

    def test_mixing1(self):
        engine = Engine(dirs=[RELATIVE])
        template = engine.get_template('dir1/two.html')
        output = template.render(Context({}))
        self.assertEqual(output.strip(), 'three two one dir2 one dir1 two')

    def test_mixing2(self):
        engine = Engine(dirs=[RELATIVE])
        template = engine.get_template('dir1/three.html')
        output = template.render(Context({}))
        self.assertEqual(output.strip(), 'three dir1 three')

    def test_mixing_loop(self):
        engine = Engine(dirs=[RELATIVE])
        msg = "Circular dependencies into relative path " \
              "'\"./dir2/../looped.html\"'"

        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            engine.render_to_string('dir1/looped.html')
