# coding: utf-8
"""
Tests for template filters (as opposed to template tags).

The tests are hidden inside a function so that things like timestamps and
timezones are only evaluated at the moment of execution and will therefore be
consistent.
"""

from datetime import datetime, timedelta

from django.utils.tzinfo import LocalTimezone
from django.utils.safestring import mark_safe

# These two classes are used to test auto-escaping of __unicode__ output.
class UnsafeClass:
    def __unicode__(self):
        return u'you & me'

class SafeClass:
    def __unicode__(self):
        return mark_safe(u'you &gt; me')

# RESULT SYNTAX --
# 'template_name': ('template contents', 'context dict',
#                   'expected string output' or Exception class)
def get_filter_tests():
    now = datetime.now()
    now_tz = datetime.now(LocalTimezone(now))
    return {
        # Default compare with datetime.now()
        'filter-timesince01' : ('{{ a|timesince }}', {'a': datetime.now() + timedelta(minutes=-1, seconds = -10)}, '1 minute'),
        'filter-timesince02' : ('{{ a|timesince }}', {'a': datetime.now() - timedelta(days=1, minutes = 1)}, '1 day'),
        'filter-timesince03' : ('{{ a|timesince }}', {'a': datetime.now() - timedelta(hours=1, minutes=25, seconds = 10)}, '1 hour, 25 minutes'),

        # Compare to a given parameter
        'filter-timesince04' : ('{{ a|timesince:b }}', {'a':now - timedelta(days=2), 'b':now - timedelta(days=1)}, '1 day'),
        'filter-timesince05' : ('{{ a|timesince:b }}', {'a':now - timedelta(days=2, minutes=1), 'b':now - timedelta(days=2)}, '1 minute'),

        # Check that timezone is respected
        'filter-timesince06' : ('{{ a|timesince:b }}', {'a':now_tz - timedelta(hours=8), 'b':now_tz}, '8 hours'),

        # Regression for #7443
        'filter-timesince07': ('{{ earlier|timesince }}', { 'earlier': now - timedelta(days=7) }, '1 week'),
        'filter-timesince08': ('{{ earlier|timesince:now }}', { 'now': now, 'earlier': now - timedelta(days=7) }, '1 week'),
        'filter-timesince09': ('{{ later|timesince }}', { 'later': now + timedelta(days=7) }, '0 minutes'),
        'filter-timesince10': ('{{ later|timesince:now }}', { 'now': now, 'later': now + timedelta(days=7) }, '0 minutes'),

        # Default compare with datetime.now()
        'filter-timeuntil01' : ('{{ a|timeuntil }}', {'a':datetime.now() + timedelta(minutes=2, seconds = 10)}, '2 minutes'),
        'filter-timeuntil02' : ('{{ a|timeuntil }}', {'a':(datetime.now() + timedelta(days=1, seconds = 10))}, '1 day'),
        'filter-timeuntil03' : ('{{ a|timeuntil }}', {'a':(datetime.now() + timedelta(hours=8, minutes=10, seconds = 10))}, '8 hours, 10 minutes'),

        # Compare to a given parameter
        'filter-timeuntil04' : ('{{ a|timeuntil:b }}', {'a':now - timedelta(days=1), 'b':now - timedelta(days=2)}, '1 day'),
        'filter-timeuntil05' : ('{{ a|timeuntil:b }}', {'a':now - timedelta(days=2), 'b':now - timedelta(days=2, minutes=1)}, '1 minute'),

        # Regression for #7443
        'filter-timeuntil06': ('{{ earlier|timeuntil }}', { 'earlier': now - timedelta(days=7) }, '0 minutes'),
        'filter-timeuntil07': ('{{ earlier|timeuntil:now }}', { 'now': now, 'earlier': now - timedelta(days=7) }, '0 minutes'),
        'filter-timeuntil08': ('{{ later|timeuntil }}', { 'later': now + timedelta(days=7) }, '1 week'),
        'filter-timeuntil09': ('{{ later|timeuntil:now }}', { 'now': now, 'earlier': now - timedelta(days=7) }, '1 week'),


        'filter-addslash01': ("{% autoescape off %}{{ a|addslashes }} {{ b|addslashes }}{% endautoescape %}", {"a": "<a>'", "b": mark_safe("<a>'")}, ur"<a>\' <a>\'"),
        'filter-addslash02': ("{{ a|addslashes }} {{ b|addslashes }}", {"a": "<a>'", "b": mark_safe("<a>'")}, ur"&lt;a&gt;\&#39; <a>\'"),

        'filter-capfirst01': ("{% autoescape off %}{{ a|capfirst }} {{ b|capfirst }}{% endautoescape %}", {"a": "fred>", "b": mark_safe("fred&gt;")}, u"Fred> Fred&gt;"),
        'filter-capfirst02': ("{{ a|capfirst }} {{ b|capfirst }}", {"a": "fred>", "b": mark_safe("fred&gt;")}, u"Fred&gt; Fred&gt;"),

        # Note that applying fix_ampsersands in autoescape mode leads to
        # double escaping.
        'filter-fix_ampersands01': ("{% autoescape off %}{{ a|fix_ampersands }} {{ b|fix_ampersands }}{% endautoescape %}", {"a": "a&b", "b": mark_safe("a&b")}, u"a&amp;b a&amp;b"),
        'filter-fix_ampersands02': ("{{ a|fix_ampersands }} {{ b|fix_ampersands }}", {"a": "a&b", "b": mark_safe("a&b")}, u"a&amp;amp;b a&amp;b"),

        'filter-floatformat01': ("{% autoescape off %}{{ a|floatformat }} {{ b|floatformat }}{% endautoescape %}", {"a": "1.42", "b": mark_safe("1.42")}, u"1.4 1.4"),
        'filter-floatformat02': ("{{ a|floatformat }} {{ b|floatformat }}", {"a": "1.42", "b": mark_safe("1.42")}, u"1.4 1.4"),

        # The contents of "linenumbers" is escaped according to the current
        # autoescape setting.
        'filter-linenumbers01': ("{{ a|linenumbers }} {{ b|linenumbers }}", {"a": "one\n<two>\nthree", "b": mark_safe("one\n&lt;two&gt;\nthree")}, u"1. one\n2. &lt;two&gt;\n3. three 1. one\n2. &lt;two&gt;\n3. three"),
        'filter-linenumbers02': ("{% autoescape off %}{{ a|linenumbers }} {{ b|linenumbers }}{% endautoescape %}", {"a": "one\n<two>\nthree", "b": mark_safe("one\n&lt;two&gt;\nthree")}, u"1. one\n2. <two>\n3. three 1. one\n2. &lt;two&gt;\n3. three"),

        'filter-lower01': ("{% autoescape off %}{{ a|lower }} {{ b|lower }}{% endautoescape %}", {"a": "Apple & banana", "b": mark_safe("Apple &amp; banana")}, u"apple & banana apple &amp; banana"),
        'filter-lower02': ("{{ a|lower }} {{ b|lower }}", {"a": "Apple & banana", "b": mark_safe("Apple &amp; banana")}, u"apple &amp; banana apple &amp; banana"),

        # The make_list filter can destroy existing escaping, so the results are
        # escaped.
        'filter-make_list01': ("{% autoescape off %}{{ a|make_list }}{% endautoescape %}", {"a": mark_safe("&")}, u"[u'&']"),
        'filter-make_list02': ("{{ a|make_list }}", {"a": mark_safe("&")}, u"[u&#39;&amp;&#39;]"),
        'filter-make_list03': ('{% autoescape off %}{{ a|make_list|stringformat:"s"|safe }}{% endautoescape %}', {"a": mark_safe("&")}, u"[u'&']"),
        'filter-make_list04': ('{{ a|make_list|stringformat:"s"|safe }}', {"a": mark_safe("&")}, u"[u'&']"),

        # Running slugify on a pre-escaped string leads to odd behaviour,
        # but the result is still safe.
        'filter-slugify01': ("{% autoescape off %}{{ a|slugify }} {{ b|slugify }}{% endautoescape %}", {"a": "a & b", "b": mark_safe("a &amp; b")}, u"a-b a-amp-b"),
        'filter-slugify02': ("{{ a|slugify }} {{ b|slugify }}", {"a": "a & b", "b": mark_safe("a &amp; b")}, u"a-b a-amp-b"),

        # Notice that escaping is applied *after* any filters, so the string
        # formatting here only needs to deal with pre-escaped characters.
        'filter-stringformat01': ('{% autoescape off %}.{{ a|stringformat:"5s" }}. .{{ b|stringformat:"5s" }}.{% endautoescape %}', {"a": "a<b", "b": mark_safe("a<b")}, u".  a<b. .  a<b."),
        'filter-stringformat02': ('.{{ a|stringformat:"5s" }}. .{{ b|stringformat:"5s" }}.', {"a": "a<b", "b": mark_safe("a<b")}, u".  a&lt;b. .  a<b."),

        # XXX No test for "title" filter; needs an actual object.

        'filter-truncatewords01': ('{% autoescape off %}{{ a|truncatewords:"2" }} {{ b|truncatewords:"2"}}{% endautoescape %}', {"a": "alpha & bravo", "b": mark_safe("alpha &amp; bravo")}, u"alpha & ... alpha &amp; ..."),
        'filter-truncatewords02': ('{{ a|truncatewords:"2" }} {{ b|truncatewords:"2"}}', {"a": "alpha & bravo", "b": mark_safe("alpha &amp; bravo")}, u"alpha &amp; ... alpha &amp; ..."),

        # The "upper" filter messes up entities (which are case-sensitive),
        # so it's not safe for non-escaping purposes.
        'filter-upper01': ('{% autoescape off %}{{ a|upper }} {{ b|upper }}{% endautoescape %}', {"a": "a & b", "b": mark_safe("a &amp; b")}, u"A & B A &AMP; B"),
        'filter-upper02': ('{{ a|upper }} {{ b|upper }}', {"a": "a & b", "b": mark_safe("a &amp; b")}, u"A &amp; B A &amp;AMP; B"),

        'filter-urlize01': ('{% autoescape off %}{{ a|urlize }} {{ b|urlize }}{% endautoescape %}', {"a": "http://example.com/?x=&y=", "b": mark_safe("http://example.com?x=&amp;y=")}, u'<a href="http://example.com/?x=&y=" rel="nofollow">http://example.com/?x=&y=</a> <a href="http://example.com?x=&amp;y=" rel="nofollow">http://example.com?x=&amp;y=</a>'),
        'filter-urlize02': ('{{ a|urlize }} {{ b|urlize }}', {"a": "http://example.com/?x=&y=", "b": mark_safe("http://example.com?x=&amp;y=")}, u'<a href="http://example.com/?x=&amp;y=" rel="nofollow">http://example.com/?x=&amp;y=</a> <a href="http://example.com?x=&amp;y=" rel="nofollow">http://example.com?x=&amp;y=</a>'),
        'filter-urlize03': ('{% autoescape off %}{{ a|urlize }}{% endautoescape %}', {"a": mark_safe("a &amp; b")}, 'a &amp; b'),
        'filter-urlize04': ('{{ a|urlize }}', {"a": mark_safe("a &amp; b")}, 'a &amp; b'),

        # This will lead to a nonsense result, but at least it won't be
        # exploitable for XSS purposes when auto-escaping is on.
        'filter-urlize05': ('{% autoescape off %}{{ a|urlize }}{% endautoescape %}', {"a": "<script>alert('foo')</script>"}, "<script>alert('foo')</script>"),
        'filter-urlize06': ('{{ a|urlize }}', {"a": "<script>alert('foo')</script>"}, '&lt;script&gt;alert(&#39;foo&#39;)&lt;/script&gt;'),

        # mailto: testing for urlize
        'filter-urlize07': ('{{ a|urlize }}', {"a": "Email me at me@example.com"}, 'Email me at <a href="mailto:me@example.com">me@example.com</a>'),
        'filter-urlize08': ('{{ a|urlize }}', {"a": "Email me at <me@example.com>"}, 'Email me at &lt;<a href="mailto:me@example.com">me@example.com</a>&gt;'),

        'filter-urlizetrunc01': ('{% autoescape off %}{{ a|urlizetrunc:"8" }} {{ b|urlizetrunc:"8" }}{% endautoescape %}', {"a": '"Unsafe" http://example.com/x=&y=', "b": mark_safe('&quot;Safe&quot; http://example.com?x=&amp;y=')}, u'"Unsafe" <a href="http://example.com/x=&y=" rel="nofollow">http:...</a> &quot;Safe&quot; <a href="http://example.com?x=&amp;y=" rel="nofollow">http:...</a>'),
        'filter-urlizetrunc02': ('{{ a|urlizetrunc:"8" }} {{ b|urlizetrunc:"8" }}', {"a": '"Unsafe" http://example.com/x=&y=', "b": mark_safe('&quot;Safe&quot; http://example.com?x=&amp;y=')}, u'&quot;Unsafe&quot; <a href="http://example.com/x=&amp;y=" rel="nofollow">http:...</a> &quot;Safe&quot; <a href="http://example.com?x=&amp;y=" rel="nofollow">http:...</a>'),

        'filter-wordcount01': ('{% autoescape off %}{{ a|wordcount }} {{ b|wordcount }}{% endautoescape %}', {"a": "a & b", "b": mark_safe("a &amp; b")}, "3 3"),
        'filter-wordcount02': ('{{ a|wordcount }} {{ b|wordcount }}', {"a": "a & b", "b": mark_safe("a &amp; b")}, "3 3"),

        'filter-wordwrap01': ('{% autoescape off %}{{ a|wordwrap:"3" }} {{ b|wordwrap:"3" }}{% endautoescape %}', {"a": "a & b", "b": mark_safe("a & b")}, u"a &\nb a &\nb"),
        'filter-wordwrap02': ('{{ a|wordwrap:"3" }} {{ b|wordwrap:"3" }}', {"a": "a & b", "b": mark_safe("a & b")}, u"a &amp;\nb a &\nb"),

        'filter-ljust01': ('{% autoescape off %}.{{ a|ljust:"5" }}. .{{ b|ljust:"5" }}.{% endautoescape %}', {"a": "a&b", "b": mark_safe("a&b")}, u".a&b  . .a&b  ."),
        'filter-ljust02': ('.{{ a|ljust:"5" }}. .{{ b|ljust:"5" }}.', {"a": "a&b", "b": mark_safe("a&b")}, u".a&amp;b  . .a&b  ."),

        'filter-rjust01': ('{% autoescape off %}.{{ a|rjust:"5" }}. .{{ b|rjust:"5" }}.{% endautoescape %}', {"a": "a&b", "b": mark_safe("a&b")}, u".  a&b. .  a&b."),
        'filter-rjust02': ('.{{ a|rjust:"5" }}. .{{ b|rjust:"5" }}.', {"a": "a&b", "b": mark_safe("a&b")}, u".  a&amp;b. .  a&b."),

        'filter-center01': ('{% autoescape off %}.{{ a|center:"5" }}. .{{ b|center:"5" }}.{% endautoescape %}', {"a": "a&b", "b": mark_safe("a&b")}, u". a&b . . a&b ."),
        'filter-center02': ('.{{ a|center:"5" }}. .{{ b|center:"5" }}.', {"a": "a&b", "b": mark_safe("a&b")}, u". a&amp;b . . a&b ."),

        'filter-cut01': ('{% autoescape off %}{{ a|cut:"x" }} {{ b|cut:"x" }}{% endautoescape %}', {"a": "x&y", "b": mark_safe("x&amp;y")}, u"&y &amp;y"),
        'filter-cut02': ('{{ a|cut:"x" }} {{ b|cut:"x" }}', {"a": "x&y", "b": mark_safe("x&amp;y")}, u"&amp;y &amp;y"),
        'filter-cut03': ('{% autoescape off %}{{ a|cut:"&" }} {{ b|cut:"&" }}{% endautoescape %}', {"a": "x&y", "b": mark_safe("x&amp;y")}, u"xy xamp;y"),
        'filter-cut04': ('{{ a|cut:"&" }} {{ b|cut:"&" }}', {"a": "x&y", "b": mark_safe("x&amp;y")}, u"xy xamp;y"),
        # Passing ';' to cut can break existing HTML entities, so those strings
        # are auto-escaped.
        'filter-cut05': ('{% autoescape off %}{{ a|cut:";" }} {{ b|cut:";" }}{% endautoescape %}', {"a": "x&y", "b": mark_safe("x&amp;y")}, u"x&y x&ampy"),
        'filter-cut06': ('{{ a|cut:";" }} {{ b|cut:";" }}', {"a": "x&y", "b": mark_safe("x&amp;y")}, u"x&amp;y x&amp;ampy"),

        # The "escape" filter works the same whether autoescape is on or off,
        # but it has no effect on strings already marked as safe.
        'filter-escape01': ('{{ a|escape }} {{ b|escape }}', {"a": "x&y", "b": mark_safe("x&y")}, u"x&amp;y x&y"),
        'filter-escape02': ('{% autoescape off %}{{ a|escape }} {{ b|escape }}{% endautoescape %}', {"a": "x&y", "b": mark_safe("x&y")}, "x&amp;y x&y"),

        # It is only applied once, regardless of the number of times it
        # appears in a chain.
        'filter-escape03': ('{% autoescape off %}{{ a|escape|escape }}{% endautoescape %}', {"a": "x&y"}, u"x&amp;y"),
        'filter-escape04': ('{{ a|escape|escape }}', {"a": "x&y"}, u"x&amp;y"),

        # Force_escape is applied immediately. It can be used to provide
        # double-escaping, for example.
        'filter-force-escape01': ('{% autoescape off %}{{ a|force_escape }}{% endautoescape %}', {"a": "x&y"}, u"x&amp;y"),
        'filter-force-escape02': ('{{ a|force_escape }}', {"a": "x&y"}, u"x&amp;y"),
        'filter-force-escape03': ('{% autoescape off %}{{ a|force_escape|force_escape }}{% endautoescape %}', {"a": "x&y"}, u"x&amp;amp;y"),
        'filter-force-escape04': ('{{ a|force_escape|force_escape }}', {"a": "x&y"}, u"x&amp;amp;y"),

        # Because the result of force_escape is "safe", an additional
        # escape filter has no effect.
        'filter-force-escape05': ('{% autoescape off %}{{ a|force_escape|escape }}{% endautoescape %}', {"a": "x&y"}, u"x&amp;y"),
        'filter-force-escape06': ('{{ a|force_escape|escape }}', {"a": "x&y"}, u"x&amp;y"),
        'filter-force-escape07': ('{% autoescape off %}{{ a|escape|force_escape }}{% endautoescape %}', {"a": "x&y"}, u"x&amp;y"),
        'filter-force-escape07': ('{{ a|escape|force_escape }}', {"a": "x&y"}, u"x&amp;y"),

        # The contents in "linebreaks" and "linebreaksbr" are escaped
        # according to the current autoescape setting.
        'filter-linebreaks01': ('{{ a|linebreaks }} {{ b|linebreaks }}', {"a": "x&\ny", "b": mark_safe("x&\ny")}, u"<p>x&amp;<br />y</p> <p>x&<br />y</p>"),
        'filter-linebreaks02': ('{% autoescape off %}{{ a|linebreaks }} {{ b|linebreaks }}{% endautoescape %}', {"a": "x&\ny", "b": mark_safe("x&\ny")}, u"<p>x&<br />y</p> <p>x&<br />y</p>"),

        'filter-linebreaksbr01': ('{{ a|linebreaksbr }} {{ b|linebreaksbr }}', {"a": "x&\ny", "b": mark_safe("x&\ny")}, u"x&amp;<br />y x&<br />y"),
        'filter-linebreaksbr02': ('{% autoescape off %}{{ a|linebreaksbr }} {{ b|linebreaksbr }}{% endautoescape %}', {"a": "x&\ny", "b": mark_safe("x&\ny")}, u"x&<br />y x&<br />y"),

        'filter-safe01': ("{{ a }} -- {{ a|safe }}", {"a": u"<b>hello</b>"}, "&lt;b&gt;hello&lt;/b&gt; -- <b>hello</b>"),
        'filter-safe02': ("{% autoescape off %}{{ a }} -- {{ a|safe }}{% endautoescape %}", {"a": "<b>hello</b>"}, u"<b>hello</b> -- <b>hello</b>"),

        'filter-removetags01': ('{{ a|removetags:"a b" }} {{ b|removetags:"a b" }}', {"a": "<a>x</a> <p><b>y</b></p>", "b": mark_safe("<a>x</a> <p><b>y</b></p>")}, u"x &lt;p&gt;y&lt;/p&gt; x <p>y</p>"),
        'filter-removetags02': ('{% autoescape off %}{{ a|removetags:"a b" }} {{ b|removetags:"a b" }}{% endautoescape %}', {"a": "<a>x</a> <p><b>y</b></p>", "b": mark_safe("<a>x</a> <p><b>y</b></p>")}, u"x <p>y</p> x <p>y</p>"),

        'filter-striptags01': ('{{ a|striptags }} {{ b|striptags }}', {"a": "<a>x</a> <p><b>y</b></p>", "b": mark_safe("<a>x</a> <p><b>y</b></p>")}, "x y x y"),
        'filter-striptags02': ('{% autoescape off %}{{ a|striptags }} {{ b|striptags }}{% endautoescape %}', {"a": "<a>x</a> <p><b>y</b></p>", "b": mark_safe("<a>x</a> <p><b>y</b></p>")}, "x y x y"),

        'filter-first01': ('{{ a|first }} {{ b|first }}', {"a": ["a&b", "x"], "b": [mark_safe("a&b"), "x"]}, "a&amp;b a&b"),
        'filter-first02': ('{% autoescape off %}{{ a|first }} {{ b|first }}{% endautoescape %}', {"a": ["a&b", "x"], "b": [mark_safe("a&b"), "x"]}, "a&b a&b"),

        'filter-last01': ('{{ a|last }} {{ b|last }}', {"a": ["x", "a&b"], "b": ["x", mark_safe("a&b")]}, "a&amp;b a&b"),
        'filter-last02': ('{% autoescape off %}{{ a|last }} {{ b|last }}{% endautoescape %}', {"a": ["x", "a&b"], "b": ["x", mark_safe("a&b")]}, "a&b a&b"),

        'filter-random01': ('{{ a|random }} {{ b|random }}', {"a": ["a&b", "a&b"], "b": [mark_safe("a&b"), mark_safe("a&b")]}, "a&amp;b a&b"),
        'filter-random02': ('{% autoescape off %}{{ a|random }} {{ b|random }}{% endautoescape %}', {"a": ["a&b", "a&b"], "b": [mark_safe("a&b"), mark_safe("a&b")]}, "a&b a&b"),

        'filter-slice01': ('{{ a|slice:"1:3" }} {{ b|slice:"1:3" }}', {"a": "a&b", "b": mark_safe("a&b")}, "&amp;b &b"),
        'filter-slice02': ('{% autoescape off %}{{ a|slice:"1:3" }} {{ b|slice:"1:3" }}{% endautoescape %}', {"a": "a&b", "b": mark_safe("a&b")}, "&b &b"),

        'filter-unordered_list01': ('{{ a|unordered_list }}', {"a": ["x>", [["<y", []]]]}, "\t<li>x&gt;\n\t<ul>\n\t\t<li>&lt;y</li>\n\t</ul>\n\t</li>"),
        'filter-unordered_list02': ('{% autoescape off %}{{ a|unordered_list }}{% endautoescape %}', {"a": ["x>", [["<y", []]]]}, "\t<li>x>\n\t<ul>\n\t\t<li><y</li>\n\t</ul>\n\t</li>"),
        'filter-unordered_list03': ('{{ a|unordered_list }}', {"a": ["x>", [[mark_safe("<y"), []]]]}, "\t<li>x&gt;\n\t<ul>\n\t\t<li><y</li>\n\t</ul>\n\t</li>"),
        'filter-unordered_list04': ('{% autoescape off %}{{ a|unordered_list }}{% endautoescape %}', {"a": ["x>", [[mark_safe("<y"), []]]]}, "\t<li>x>\n\t<ul>\n\t\t<li><y</li>\n\t</ul>\n\t</li>"),
        'filter-unordered_list05': ('{% autoescape off %}{{ a|unordered_list }}{% endautoescape %}', {"a": ["x>", [["<y", []]]]}, "\t<li>x>\n\t<ul>\n\t\t<li><y</li>\n\t</ul>\n\t</li>"),

        # Literal string arguments to the default filter are always treated as
        # safe strings, regardless of the auto-escaping state.
        #
        # Note: we have to use {"a": ""} here, otherwise the invalid template
        # variable string interferes with the test result.
        'filter-default01': ('{{ a|default:"x<" }}', {"a": ""}, "x<"),
        'filter-default02': ('{% autoescape off %}{{ a|default:"x<" }}{% endautoescape %}', {"a": ""}, "x<"),
        'filter-default03': ('{{ a|default:"x<" }}', {"a": mark_safe("x>")}, "x>"),
        'filter-default04': ('{% autoescape off %}{{ a|default:"x<" }}{% endautoescape %}', {"a": mark_safe("x>")}, "x>"),

        'filter-default_if_none01': ('{{ a|default:"x<" }}', {"a": None}, "x<"),
        'filter-default_if_none02': ('{% autoescape off %}{{ a|default:"x<" }}{% endautoescape %}', {"a": None}, "x<"),

        'filter-phone2numeric01': ('{{ a|phone2numeric }} {{ b|phone2numeric }}', {"a": "<1-800-call-me>", "b": mark_safe("<1-800-call-me>") }, "&lt;1-800-2255-63&gt; <1-800-2255-63>"),
        'filter-phone2numeric02': ('{% autoescape off %}{{ a|phone2numeric }} {{ b|phone2numeric }}{% endautoescape %}', {"a": "<1-800-call-me>", "b": mark_safe("<1-800-call-me>") }, "<1-800-2255-63> <1-800-2255-63>"),

        # Ensure iriencode keeps safe strings:
        'filter-iriencode01': ('{{ url|iriencode }}', {'url': '?test=1&me=2'}, '?test=1&amp;me=2'),
        'filter-iriencode02': ('{% autoescape off %}{{ url|iriencode }}{% endautoescape %}', {'url': '?test=1&me=2'}, '?test=1&me=2'),
        'filter-iriencode03': ('{{ url|iriencode }}', {'url': mark_safe('?test=1&me=2')}, '?test=1&me=2'),
        'filter-iriencode04': ('{% autoescape off %}{{ url|iriencode }}{% endautoescape %}', {'url': mark_safe('?test=1&me=2')}, '?test=1&me=2'),

        # Chaining a bunch of safeness-preserving filters should not alter
        # the safe status either way.
        'chaining01': ('{{ a|capfirst|center:"7" }}.{{ b|capfirst|center:"7" }}', {"a": "a < b", "b": mark_safe("a < b")}, " A &lt; b . A < b "),
        'chaining02': ('{% autoescape off %}{{ a|capfirst|center:"7" }}.{{ b|capfirst|center:"7" }}{% endautoescape %}', {"a": "a < b", "b": mark_safe("a < b")}, " A < b . A < b "),

        # Using a filter that forces a string back to unsafe:
        'chaining03': ('{{ a|cut:"b"|capfirst }}.{{ b|cut:"b"|capfirst }}', {"a": "a < b", "b": mark_safe("a < b")}, "A &lt; .A < "),
        'chaining04': ('{% autoescape off %}{{ a|cut:"b"|capfirst }}.{{ b|cut:"b"|capfirst }}{% endautoescape %}', {"a": "a < b", "b": mark_safe("a < b")}, "A < .A < "),

        # Using a filter that forces safeness does not lead to double-escaping
        'chaining05': ('{{ a|escape|capfirst }}', {"a": "a < b"}, "A &lt; b"),
        'chaining06': ('{% autoescape off %}{{ a|escape|capfirst }}{% endautoescape %}', {"a": "a < b"}, "A &lt; b"),

        # Force to safe, then back (also showing why using force_escape too
        # early in a chain can lead to unexpected results).
        'chaining07': ('{{ a|force_escape|cut:";" }}', {"a": "a < b"}, "a &amp;lt b"),
        'chaining08': ('{% autoescape off %}{{ a|force_escape|cut:";" }}{% endautoescape %}', {"a": "a < b"}, "a &lt b"),
        'chaining09': ('{{ a|cut:";"|force_escape }}', {"a": "a < b"}, "a &lt; b"),
        'chaining10': ('{% autoescape off %}{{ a|cut:";"|force_escape }}{% endautoescape %}', {"a": "a < b"}, "a &lt; b"),
        'chaining11': ('{{ a|cut:"b"|safe }}', {"a": "a < b"}, "a < "),
        'chaining12': ('{% autoescape off %}{{ a|cut:"b"|safe }}{% endautoescape %}', {"a": "a < b"}, "a < "),
        'chaining13': ('{{ a|safe|force_escape }}', {"a": "a < b"}, "a &lt; b"),
        'chaining14': ('{% autoescape off %}{{ a|safe|force_escape }}{% endautoescape %}', {"a": "a < b"}, "a &lt; b"),

        # Filters decorated with stringfilter still respect is_safe.
        'autoescape-stringfilter01': (r'{{ unsafe|capfirst }}', {'unsafe': UnsafeClass()}, 'You &amp; me'),
        'autoescape-stringfilter02': (r'{% autoescape off %}{{ unsafe|capfirst }}{% endautoescape %}', {'unsafe': UnsafeClass()}, 'You & me'),
        'autoescape-stringfilter03': (r'{{ safe|capfirst }}', {'safe': SafeClass()}, 'You &gt; me'),
        'autoescape-stringfilter04': (r'{% autoescape off %}{{ safe|capfirst }}{% endautoescape %}', {'safe': SafeClass()}, 'You &gt; me'),
    }

