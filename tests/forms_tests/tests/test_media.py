from django.forms import CharField, Form, Media, MultiWidget, TextInput
from django.template import Context, Template
from django.templatetags.static import static
from django.test import SimpleTestCase, override_settings
from django.utils.html import format_html, html_safe


@override_settings(
    STATIC_URL="http://media.example.com/static/",
)
class FormsMediaTestCase(SimpleTestCase):
    """Tests for the media handling on widgets and forms"""

    def test_construction(self):
        # Check construction of media objects
        m = Media(
            css={"all": ("path/to/css1", "/path/to/css2")},
            js=(
                "/path/to/js1",
                "http://media.other.com/path/to/js2",
                "https://secure.other.com/path/to/js3",
            ),
        )
        self.assertEqual(
            str(m),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>',
        )
        self.assertEqual(
            repr(m),
            "Media(css={'all': ['path/to/css1', '/path/to/css2']}, "
            "js=['/path/to/js1', 'http://media.other.com/path/to/js2', "
            "'https://secure.other.com/path/to/js3'])",
        )

        class Foo:
            css = {"all": ("path/to/css1", "/path/to/css2")}
            js = (
                "/path/to/js1",
                "http://media.other.com/path/to/js2",
                "https://secure.other.com/path/to/js3",
            )

        m3 = Media(Foo)
        self.assertEqual(
            str(m3),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>',
        )

        # A widget can exist without a media definition
        class MyWidget(TextInput):
            pass

        w = MyWidget()
        self.assertEqual(str(w.media), "")

    def test_media_dsl(self):
        ###############################################################
        # DSL Class-based media definitions
        ###############################################################

        # A widget can define media if it needs to.
        # Any absolute path will be preserved; relative paths are combined
        # with the value of settings.MEDIA_URL
        class MyWidget1(TextInput):
            class Media:
                css = {"all": ("path/to/css1", "/path/to/css2")}
                js = (
                    "/path/to/js1",
                    "http://media.other.com/path/to/js2",
                    "https://secure.other.com/path/to/js3",
                )

        w1 = MyWidget1()
        self.assertEqual(
            str(w1.media),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>',
        )

        # Media objects can be interrogated by media type
        self.assertEqual(
            str(w1.media["css"]),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">',
        )

        self.assertEqual(
            str(w1.media["js"]),
            """<script src="/path/to/js1"></script>
<script src="http://media.other.com/path/to/js2"></script>
<script src="https://secure.other.com/path/to/js3"></script>""",
        )

    def test_combine_media(self):
        # Media objects can be combined. Any given media resource will appear only
        # once. Duplicated media definitions are ignored.
        class MyWidget1(TextInput):
            class Media:
                css = {"all": ("path/to/css1", "/path/to/css2")}
                js = (
                    "/path/to/js1",
                    "http://media.other.com/path/to/js2",
                    "https://secure.other.com/path/to/js3",
                )

        class MyWidget2(TextInput):
            class Media:
                css = {"all": ("/path/to/css2", "/path/to/css3")}
                js = ("/path/to/js1", "/path/to/js4")

        class MyWidget3(TextInput):
            class Media:
                css = {"all": ("path/to/css1", "/path/to/css3")}
                js = ("/path/to/js1", "/path/to/js4")

        w1 = MyWidget1()
        w2 = MyWidget2()
        w3 = MyWidget3()
        self.assertEqual(
            str(w1.media + w2.media + w3.media),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<link href="/path/to/css3" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="/path/to/js4"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>',
        )

        # media addition hasn't affected the original objects
        self.assertEqual(
            str(w1.media),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>',
        )

        # Regression check for #12879: specifying the same CSS or JS file
        # multiple times in a single Media instance should result in that file
        # only being included once.
        class MyWidget4(TextInput):
            class Media:
                css = {"all": ("/path/to/css1", "/path/to/css1")}
                js = ("/path/to/js1", "/path/to/js1")

        w4 = MyWidget4()
        self.assertEqual(
            str(w4.media),
            """<link href="/path/to/css1" media="all" rel="stylesheet">
<script src="/path/to/js1"></script>""",
        )

    def test_media_deduplication(self):
        # A deduplication test applied directly to a Media object, to confirm
        # that the deduplication doesn't only happen at the point of merging
        # two or more media objects.
        media = Media(
            css={"all": ("/path/to/css1", "/path/to/css1")},
            js=("/path/to/js1", "/path/to/js1"),
        )
        self.assertEqual(
            str(media),
            """<link href="/path/to/css1" media="all" rel="stylesheet">
<script src="/path/to/js1"></script>""",
        )

    def test_media_property(self):
        ###############################################################
        # Property-based media definitions
        ###############################################################

        # Widget media can be defined as a property
        class MyWidget4(TextInput):
            def _media(self):
                return Media(css={"all": ("/some/path",)}, js=("/some/js",))

            media = property(_media)

        w4 = MyWidget4()
        self.assertEqual(
            str(w4.media),
            """<link href="/some/path" media="all" rel="stylesheet">
<script src="/some/js"></script>""",
        )

        # Media properties can reference the media of their parents
        class MyWidget5(MyWidget4):
            def _media(self):
                return super().media + Media(
                    css={"all": ("/other/path",)}, js=("/other/js",)
                )

            media = property(_media)

        w5 = MyWidget5()
        self.assertEqual(
            str(w5.media),
            """<link href="/some/path" media="all" rel="stylesheet">
<link href="/other/path" media="all" rel="stylesheet">
<script src="/some/js"></script>
<script src="/other/js"></script>""",
        )

    def test_media_property_parent_references(self):
        # Media properties can reference the media of their parents,
        # even if the parent media was defined using a class
        class MyWidget1(TextInput):
            class Media:
                css = {"all": ("path/to/css1", "/path/to/css2")}
                js = (
                    "/path/to/js1",
                    "http://media.other.com/path/to/js2",
                    "https://secure.other.com/path/to/js3",
                )

        class MyWidget6(MyWidget1):
            def _media(self):
                return super().media + Media(
                    css={"all": ("/other/path",)}, js=("/other/js",)
                )

            media = property(_media)

        w6 = MyWidget6()
        self.assertEqual(
            str(w6.media),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/other/path" media="all" rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="/other/js"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>',
        )

    def test_media_inheritance(self):
        ###############################################################
        # Inheritance of media
        ###############################################################

        # If a widget extends another but provides no media definition, it
        # inherits the parent widget's media.
        class MyWidget1(TextInput):
            class Media:
                css = {"all": ("path/to/css1", "/path/to/css2")}
                js = (
                    "/path/to/js1",
                    "http://media.other.com/path/to/js2",
                    "https://secure.other.com/path/to/js3",
                )

        class MyWidget7(MyWidget1):
            pass

        w7 = MyWidget7()
        self.assertEqual(
            str(w7.media),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>',
        )

        # If a widget extends another but defines media, it extends the parent
        # widget's media by default.
        class MyWidget8(MyWidget1):
            class Media:
                css = {"all": ("/path/to/css3", "path/to/css1")}
                js = ("/path/to/js1", "/path/to/js4")

        w8 = MyWidget8()
        self.assertEqual(
            str(w8.media),
            """<link href="/path/to/css3" media="all" rel="stylesheet">
<link href="http://media.example.com/static/path/to/css1" media="all" rel="stylesheet">
<link href="/path/to/css2" media="all" rel="stylesheet">
<script src="/path/to/js1"></script>
<script src="http://media.other.com/path/to/js2"></script>
<script src="/path/to/js4"></script>
<script src="https://secure.other.com/path/to/js3"></script>""",
        )

    def test_media_inheritance_from_property(self):
        # If a widget extends another but defines media, it extends the parents
        # widget's media, even if the parent defined media using a property.
        class MyWidget1(TextInput):
            class Media:
                css = {"all": ("path/to/css1", "/path/to/css2")}
                js = (
                    "/path/to/js1",
                    "http://media.other.com/path/to/js2",
                    "https://secure.other.com/path/to/js3",
                )

        class MyWidget4(TextInput):
            def _media(self):
                return Media(css={"all": ("/some/path",)}, js=("/some/js",))

            media = property(_media)

        class MyWidget9(MyWidget4):
            class Media:
                css = {"all": ("/other/path",)}
                js = ("/other/js",)

        w9 = MyWidget9()
        self.assertEqual(
            str(w9.media),
            """<link href="/some/path" media="all" rel="stylesheet">
<link href="/other/path" media="all" rel="stylesheet">
<script src="/some/js"></script>
<script src="/other/js"></script>""",
        )

        # A widget can disable media inheritance by specifying 'extend=False'
        class MyWidget10(MyWidget1):
            class Media:
                extend = False
                css = {"all": ("/path/to/css3", "path/to/css1")}
                js = ("/path/to/js1", "/path/to/js4")

        w10 = MyWidget10()
        self.assertEqual(
            str(w10.media),
            """<link href="/path/to/css3" media="all" rel="stylesheet">
<link href="http://media.example.com/static/path/to/css1" media="all" rel="stylesheet">
<script src="/path/to/js1"></script>
<script src="/path/to/js4"></script>""",
        )

    def test_media_inheritance_extends(self):
        # A widget can explicitly enable full media inheritance by specifying
        # 'extend=True'.
        class MyWidget1(TextInput):
            class Media:
                css = {"all": ("path/to/css1", "/path/to/css2")}
                js = (
                    "/path/to/js1",
                    "http://media.other.com/path/to/js2",
                    "https://secure.other.com/path/to/js3",
                )

        class MyWidget11(MyWidget1):
            class Media:
                extend = True
                css = {"all": ("/path/to/css3", "path/to/css1")}
                js = ("/path/to/js1", "/path/to/js4")

        w11 = MyWidget11()
        self.assertEqual(
            str(w11.media),
            """<link href="/path/to/css3" media="all" rel="stylesheet">
<link href="http://media.example.com/static/path/to/css1" media="all" rel="stylesheet">
<link href="/path/to/css2" media="all" rel="stylesheet">
<script src="/path/to/js1"></script>
<script src="http://media.other.com/path/to/js2"></script>
<script src="/path/to/js4"></script>
<script src="https://secure.other.com/path/to/js3"></script>""",
        )

    def test_media_inheritance_single_type(self):
        # A widget can enable inheritance of one media type by specifying
        # extend as a tuple.
        class MyWidget1(TextInput):
            class Media:
                css = {"all": ("path/to/css1", "/path/to/css2")}
                js = (
                    "/path/to/js1",
                    "http://media.other.com/path/to/js2",
                    "https://secure.other.com/path/to/js3",
                )

        class MyWidget12(MyWidget1):
            class Media:
                extend = ("css",)
                css = {"all": ("/path/to/css3", "path/to/css1")}
                js = ("/path/to/js1", "/path/to/js4")

        w12 = MyWidget12()
        self.assertEqual(
            str(w12.media),
            """<link href="/path/to/css3" media="all" rel="stylesheet">
<link href="http://media.example.com/static/path/to/css1" media="all" rel="stylesheet">
<link href="/path/to/css2" media="all" rel="stylesheet">
<script src="/path/to/js1"></script>
<script src="/path/to/js4"></script>""",
        )

    def test_multi_media(self):
        ###############################################################
        # Multi-media handling for CSS
        ###############################################################

        # A widget can define CSS media for multiple output media types
        class MultimediaWidget(TextInput):
            class Media:
                css = {
                    "screen, print": ("/file1", "/file2"),
                    "screen": ("/file3",),
                    "print": ("/file4",),
                }
                js = ("/path/to/js1", "/path/to/js4")

        multimedia = MultimediaWidget()
        self.assertEqual(
            str(multimedia.media),
            """<link href="/file4" media="print" rel="stylesheet">
<link href="/file3" media="screen" rel="stylesheet">
<link href="/file1" media="screen, print" rel="stylesheet">
<link href="/file2" media="screen, print" rel="stylesheet">
<script src="/path/to/js1"></script>
<script src="/path/to/js4"></script>""",
        )

    def test_multi_widget(self):
        ###############################################################
        # Multiwidget media handling
        ###############################################################

        class MyWidget1(TextInput):
            class Media:
                css = {"all": ("path/to/css1", "/path/to/css2")}
                js = (
                    "/path/to/js1",
                    "http://media.other.com/path/to/js2",
                    "https://secure.other.com/path/to/js3",
                )

        class MyWidget2(TextInput):
            class Media:
                css = {"all": ("/path/to/css2", "/path/to/css3")}
                js = ("/path/to/js1", "/path/to/js4")

        class MyWidget3(TextInput):
            class Media:
                css = {"all": ("path/to/css1", "/path/to/css3")}
                js = ("/path/to/js1", "/path/to/js4")

        # MultiWidgets have a default media definition that gets all the
        # media from the component widgets
        class MyMultiWidget(MultiWidget):
            def __init__(self, attrs=None):
                widgets = [MyWidget1, MyWidget2, MyWidget3]
                super().__init__(widgets, attrs)

        mymulti = MyMultiWidget()
        self.assertEqual(
            str(mymulti.media),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<link href="/path/to/css3" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="/path/to/js4"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>',
        )

    def test_form_media(self):
        ###############################################################
        # Media processing for forms
        ###############################################################

        class MyWidget1(TextInput):
            class Media:
                css = {"all": ("path/to/css1", "/path/to/css2")}
                js = (
                    "/path/to/js1",
                    "http://media.other.com/path/to/js2",
                    "https://secure.other.com/path/to/js3",
                )

        class MyWidget2(TextInput):
            class Media:
                css = {"all": ("/path/to/css2", "/path/to/css3")}
                js = ("/path/to/js1", "/path/to/js4")

        class MyWidget3(TextInput):
            class Media:
                css = {"all": ("path/to/css1", "/path/to/css3")}
                js = ("/path/to/js1", "/path/to/js4")

        # You can ask a form for the media required by its widgets.
        class MyForm(Form):
            field1 = CharField(max_length=20, widget=MyWidget1())
            field2 = CharField(max_length=20, widget=MyWidget2())

        f1 = MyForm()
        self.assertEqual(
            str(f1.media),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<link href="/path/to/css3" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="/path/to/js4"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>',
        )

        # Form media can be combined to produce a single media definition.
        class AnotherForm(Form):
            field3 = CharField(max_length=20, widget=MyWidget3())

        f2 = AnotherForm()
        self.assertEqual(
            str(f1.media + f2.media),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<link href="/path/to/css3" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="/path/to/js4"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>',
        )

        # Forms can also define media, following the same rules as widgets.
        class FormWithMedia(Form):
            field1 = CharField(max_length=20, widget=MyWidget1())
            field2 = CharField(max_length=20, widget=MyWidget2())

            class Media:
                js = ("/some/form/javascript",)
                css = {"all": ("/some/form/css",)}

        f3 = FormWithMedia()
        self.assertEqual(
            str(f3.media),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/some/form/css" media="all" rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<link href="/path/to/css3" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="/some/form/javascript"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="/path/to/js4"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>',
        )

        # Media works in templates
        self.assertEqual(
            Template("{{ form.media.js }}{{ form.media.css }}").render(
                Context({"form": f3})
            ),
            '<script src="/path/to/js1"></script>\n'
            '<script src="/some/form/javascript"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="/path/to/js4"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>'
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/some/form/css" media="all" rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<link href="/path/to/css3" media="all" rel="stylesheet">',
        )

    def test_html_safe(self):
        media = Media(css={"all": ["/path/to/css"]}, js=["/path/to/js"])
        self.assertTrue(hasattr(Media, "__html__"))
        self.assertEqual(str(media), media.__html__())

    def test_merge(self):
        test_values = (
            (([1, 2], [3, 4]), [1, 3, 2, 4]),
            (([1, 2], [2, 3]), [1, 2, 3]),
            (([2, 3], [1, 2]), [1, 2, 3]),
            (([1, 3], [2, 3]), [1, 2, 3]),
            (([1, 2], [1, 3]), [1, 2, 3]),
            (([1, 2], [3, 2]), [1, 3, 2]),
            (([1, 2], [1, 2]), [1, 2]),
            (
                [[1, 2], [1, 3], [2, 3], [5, 7], [5, 6], [6, 7, 9], [8, 9]],
                [1, 5, 8, 2, 6, 3, 7, 9],
            ),
            ((), []),
            (([1, 2],), [1, 2]),
        )
        for lists, expected in test_values:
            with self.subTest(lists=lists):
                self.assertEqual(Media.merge(*lists), expected)

    def test_merge_warning(self):
        msg = "Detected duplicate Media files in an opposite order: [1, 2], [2, 1]"
        with self.assertWarnsMessage(RuntimeWarning, msg):
            self.assertEqual(Media.merge([1, 2], [2, 1]), [1, 2])

    def test_merge_js_three_way(self):
        """
        The relative order of scripts is preserved in a three-way merge.
        """
        widget1 = Media(js=["color-picker.js"])
        widget2 = Media(js=["text-editor.js"])
        widget3 = Media(
            js=["text-editor.js", "text-editor-extras.js", "color-picker.js"]
        )
        merged = widget1 + widget2 + widget3
        self.assertEqual(
            merged._js, ["text-editor.js", "text-editor-extras.js", "color-picker.js"]
        )

    def test_merge_js_three_way2(self):
        # The merge prefers to place 'c' before 'b' and 'g' before 'h' to
        # preserve the original order. The preference 'c'->'b' is overridden by
        # widget3's media, but 'g'->'h' survives in the final ordering.
        widget1 = Media(js=["a", "c", "f", "g", "k"])
        widget2 = Media(js=["a", "b", "f", "h", "k"])
        widget3 = Media(js=["b", "c", "f", "k"])
        merged = widget1 + widget2 + widget3
        self.assertEqual(merged._js, ["a", "b", "c", "f", "g", "h", "k"])

    def test_merge_css_three_way(self):
        widget1 = Media(css={"screen": ["c.css"], "all": ["d.css", "e.css"]})
        widget2 = Media(css={"screen": ["a.css"]})
        widget3 = Media(css={"screen": ["a.css", "b.css", "c.css"], "all": ["e.css"]})
        widget4 = Media(css={"all": ["d.css", "e.css"], "screen": ["c.css"]})
        merged = widget1 + widget2
        # c.css comes before a.css because widget1 + widget2 establishes this
        # order.
        self.assertEqual(
            merged._css, {"screen": ["c.css", "a.css"], "all": ["d.css", "e.css"]}
        )
        merged += widget3
        # widget3 contains an explicit ordering of c.css and a.css.
        self.assertEqual(
            merged._css,
            {"screen": ["a.css", "b.css", "c.css"], "all": ["d.css", "e.css"]},
        )
        # Media ordering does not matter.
        merged = widget1 + widget4
        self.assertEqual(merged._css, {"screen": ["c.css"], "all": ["d.css", "e.css"]})

    def test_add_js_deduplication(self):
        widget1 = Media(js=["a", "b", "c"])
        widget2 = Media(js=["a", "b"])
        widget3 = Media(js=["a", "c", "b"])
        merged = widget1 + widget1
        self.assertEqual(merged._js_lists, [["a", "b", "c"]])
        self.assertEqual(merged._js, ["a", "b", "c"])
        merged = widget1 + widget2
        self.assertEqual(merged._js_lists, [["a", "b", "c"], ["a", "b"]])
        self.assertEqual(merged._js, ["a", "b", "c"])
        # Lists with items in a different order are preserved when added.
        merged = widget1 + widget3
        self.assertEqual(merged._js_lists, [["a", "b", "c"], ["a", "c", "b"]])
        msg = (
            "Detected duplicate Media files in an opposite order: "
            "['a', 'b', 'c'], ['a', 'c', 'b']"
        )
        with self.assertWarnsMessage(RuntimeWarning, msg):
            merged._js

    def test_add_css_deduplication(self):
        widget1 = Media(css={"screen": ["a.css"], "all": ["b.css"]})
        widget2 = Media(css={"screen": ["c.css"]})
        widget3 = Media(css={"screen": ["a.css"], "all": ["b.css", "c.css"]})
        widget4 = Media(css={"screen": ["a.css"], "all": ["c.css", "b.css"]})
        merged = widget1 + widget1
        self.assertEqual(merged._css_lists, [{"screen": ["a.css"], "all": ["b.css"]}])
        self.assertEqual(merged._css, {"screen": ["a.css"], "all": ["b.css"]})
        merged = widget1 + widget2
        self.assertEqual(
            merged._css_lists,
            [
                {"screen": ["a.css"], "all": ["b.css"]},
                {"screen": ["c.css"]},
            ],
        )
        self.assertEqual(merged._css, {"screen": ["a.css", "c.css"], "all": ["b.css"]})
        merged = widget3 + widget4
        # Ordering within lists is preserved.
        self.assertEqual(
            merged._css_lists,
            [
                {"screen": ["a.css"], "all": ["b.css", "c.css"]},
                {"screen": ["a.css"], "all": ["c.css", "b.css"]},
            ],
        )
        msg = (
            "Detected duplicate Media files in an opposite order: "
            "['b.css', 'c.css'], ['c.css', 'b.css']"
        )
        with self.assertWarnsMessage(RuntimeWarning, msg):
            merged._css

    def test_add_empty(self):
        media = Media(css={"screen": ["a.css"]}, js=["a"])
        empty_media = Media()
        merged = media + empty_media
        self.assertEqual(merged._css_lists, [{"screen": ["a.css"]}])
        self.assertEqual(merged._js_lists, [["a"]])


@html_safe
class Asset:
    def __init__(self, path):
        self.path = path

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and self.path == other.path) or (
            other.__class__ == str and self.path == other
        )

    def __hash__(self):
        return hash(self.path)

    def __str__(self):
        return self.absolute_path(self.path)

    def absolute_path(self, path):
        """
        Given a relative or absolute path to a static asset, return an absolute
        path. An absolute path will be returned unchanged while a relative path
        will be passed to django.templatetags.static.static().
        """
        if path.startswith(("http://", "https://", "/")):
            return path
        return static(path)

    def __repr__(self):
        return f"{self.path!r}"


class CSS(Asset):
    def __init__(self, path, medium):
        super().__init__(path)
        self.medium = medium

    def __str__(self):
        path = super().__str__()
        return format_html(
            '<link href="{}" media="{}" rel="stylesheet">',
            self.absolute_path(path),
            self.medium,
        )


class JS(Asset):
    def __init__(self, path, integrity=None):
        super().__init__(path)
        self.integrity = integrity or ""

    def __str__(self, integrity=None):
        path = super().__str__()
        template = '<script src="{}"%s></script>' % (
            ' integrity="{}"' if self.integrity else "{}"
        )
        return format_html(template, self.absolute_path(path), self.integrity)


@override_settings(
    STATIC_URL="http://media.example.com/static/",
)
class FormsMediaObjectTestCase(SimpleTestCase):
    """Media handling when media are objects instead of raw strings."""

    def test_construction(self):
        m = Media(
            css={"all": (CSS("path/to/css1", "all"), CSS("/path/to/css2", "all"))},
            js=(
                JS("/path/to/js1"),
                JS("http://media.other.com/path/to/js2"),
                JS(
                    "https://secure.other.com/path/to/js3",
                    integrity="9d947b87fdeb25030d56d01f7aa75800",
                ),
            ),
        )
        self.assertEqual(
            str(m),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="https://secure.other.com/path/to/js3" '
            'integrity="9d947b87fdeb25030d56d01f7aa75800"></script>',
        )
        self.assertEqual(
            repr(m),
            "Media(css={'all': ['path/to/css1', '/path/to/css2']}, "
            "js=['/path/to/js1', 'http://media.other.com/path/to/js2', "
            "'https://secure.other.com/path/to/js3'])",
        )

    def test_simplest_class(self):
        @html_safe
        class SimpleJS:
            """The simplest possible asset class."""

            def __str__(self):
                return '<script src="https://example.org/asset.js" rel="stylesheet">'

        m = Media(js=(SimpleJS(),))
        self.assertEqual(
            str(m),
            '<script src="https://example.org/asset.js" rel="stylesheet">',
        )

    def test_combine_media(self):
        class MyWidget1(TextInput):
            class Media:
                css = {"all": (CSS("path/to/css1", "all"), "/path/to/css2")}
                js = (
                    "/path/to/js1",
                    "http://media.other.com/path/to/js2",
                    "https://secure.other.com/path/to/js3",
                    JS("/path/to/js4", integrity="9d947b87fdeb25030d56d01f7aa75800"),
                )

        class MyWidget2(TextInput):
            class Media:
                css = {"all": (CSS("/path/to/css2", "all"), "/path/to/css3")}
                js = (JS("/path/to/js1"), "/path/to/js4")

        w1 = MyWidget1()
        w2 = MyWidget2()
        self.assertEqual(
            str(w1.media + w2.media),
            '<link href="http://media.example.com/static/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<link href="/path/to/css3" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>\n'
            '<script src="/path/to/js4" integrity="9d947b87fdeb25030d56d01f7aa75800">'
            "</script>",
        )

    def test_media_deduplication(self):
        # The deduplication doesn't only happen at the point of merging two or
        # more media objects.
        media = Media(
            css={
                "all": (
                    CSS("/path/to/css1", "all"),
                    CSS("/path/to/css1", "all"),
                    "/path/to/css1",
                )
            },
            js=(JS("/path/to/js1"), JS("/path/to/js1"), "/path/to/js1"),
        )
        self.assertEqual(
            str(media),
            '<link href="/path/to/css1" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>',
        )
