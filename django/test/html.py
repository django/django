"""Compare two HTML documents."""
import html
from html.parser import HTMLParser

from django.utils.regex_helper import _lazy_re_compile

# ASCII whitespace is U+0009 TAB, U+000A LF, U+000C FF, U+000D CR, or U+0020
# SPACE.
# https://infra.spec.whatwg.org/#ascii-whitespace
ASCII_WHITESPACE = _lazy_re_compile(r"[\t\n\f\r ]+")

# https://html.spec.whatwg.org/#attributes-3
BOOLEAN_ATTRIBUTES = {
    "allowfullscreen",
    "async",
    "autofocus",
    "autoplay",
    "checked",
    "controls",
    "default",
    "defer ",
    "disabled",
    "formnovalidate",
    "hidden",
    "ismap",
    "itemscope",
    "loop",
    "multiple",
    "muted",
    "nomodule",
    "novalidate",
    "open",
    "playsinline",
    "readonly",
    "required",
    "reversed",
    "selected",
    # Attributes for deprecated tags.
    "truespeed",
}


def normalize_whitespace(string):
    return ASCII_WHITESPACE.sub(" ", string)


def normalize_attributes(attributes):
    normalized = []
    for name, value in attributes:
        if name == "class" and value:
            # Special case handling of 'class' attribute, so that comparisons
            # of DOM instances are not sensitive to ordering of classes.
            value = " ".join(
                sorted(value for value in ASCII_WHITESPACE.split(value) if value)
            )
        # Boolean attributes without a value is same as attribute with value
        # that equals the attributes name. For example:
        #   <input checked> == <input checked="checked">
        if name in BOOLEAN_ATTRIBUTES:
            if not value or value == name:
                value = None
        elif value is None:
            value = ""
        normalized.append((name, value))
    return normalized


class Element:
    def __init__(self, name, attributes):
        self.name = name
        self.attributes = sorted(attributes)
        self.children = []

    def append(self, element):
        if isinstance(element, str):
            element = normalize_whitespace(element)
            if self.children and isinstance(self.children[-1], str):
                self.children[-1] += element
                self.children[-1] = normalize_whitespace(self.children[-1])
                return
        elif self.children:
            # removing last children if it is only whitespace
            # this can result in incorrect dom representations since
            # whitespace between inline tags like <span> is significant
            if isinstance(self.children[-1], str) and self.children[-1].isspace():
                self.children.pop()
        if element:
            self.children.append(element)

    def finalize(self):
        def rstrip_last_element(children):
            if children and isinstance(children[-1], str):
                children[-1] = children[-1].rstrip()
                if not children[-1]:
                    children.pop()
                    children = rstrip_last_element(children)
            return children

        rstrip_last_element(self.children)
        for i, child in enumerate(self.children):
            if isinstance(child, str):
                self.children[i] = child.strip()
            elif hasattr(child, "finalize"):
                child.finalize()

    def __eq__(self, element):
        if not hasattr(element, "name") or self.name != element.name:
            return False
        if self.attributes != element.attributes:
            return False
        return self.children == element.children

    def __hash__(self):
        return hash((self.name, *self.attributes))

    def _count(self, element, count=True):
        if not isinstance(element, str) and self == element:
            return 1
        if isinstance(element, RootElement) and self.children == element.children:
            return 1
        i = 0
        elem_child_idx = 0
        for child in self.children:
            # child is text content and element is also text content, then
            # make a simple "text" in "text"
            if isinstance(child, str):
                if isinstance(element, str):
                    if count:
                        i += child.count(element)
                    elif element in child:
                        return 1
            else:
                # Look for element wholly within this child.
                i += child._count(element, count=count)
                if not count and i:
                    return i
                # Also look for a sequence of element's children among self's
                # children. self.children == element.children is tested above,
                # but will fail if self has additional children. Ex: '<a/><b/>'
                # is contained in '<a/><b/><c/>'.
                if isinstance(element, RootElement) and element.children:
                    elem_child = element.children[elem_child_idx]
                    # Start or continue match, advance index.
                    if elem_child == child:
                        elem_child_idx += 1
                        # Match found, reset index.
                        if elem_child_idx == len(element.children):
                            i += 1
                            elem_child_idx = 0
                    # No match, reset index.
                    else:
                        elem_child_idx = 0
        return i

    def __contains__(self, element):
        return self._count(element, count=False) > 0

    def count(self, element):
        return self._count(element, count=True)

    def __getitem__(self, key):
        return self.children[key]

    def __str__(self):
        output = "<%s" % self.name
        for key, value in self.attributes:
            if value is not None:
                output += ' %s="%s"' % (key, value)
            else:
                output += " %s" % key
        if self.children:
            output += ">\n"
            output += "".join(
                [
                    html.escape(c) if isinstance(c, str) else str(c)
                    for c in self.children
                ]
            )
            output += "\n</%s>" % self.name
        else:
            output += ">"
        return output

    def __repr__(self):
        return str(self)


class RootElement(Element):
    def __init__(self):
        super().__init__(None, ())

    def __str__(self):
        return "".join(
            [html.escape(c) if isinstance(c, str) else str(c) for c in self.children]
        )


class HTMLParseError(Exception):
    pass


class Parser(HTMLParser):
    # https://html.spec.whatwg.org/#void-elements
    SELF_CLOSING_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
        # Deprecated tags
        "frame",
        "spacer",
    }

    def __init__(self):
        super().__init__()
        self.root = RootElement()
        self.open_tags = []
        self.element_positions = {}

    def error(self, msg):
        raise HTMLParseError(msg, self.getpos())

    def format_position(self, position=None, element=None):
        if not position and element:
            position = self.element_positions[element]
        if position is None:
            position = self.getpos()
        if hasattr(position, "lineno"):
            position = position.lineno, position.offset
        return "Line %d, Column %d" % position

    @property
    def current(self):
        if self.open_tags:
            return self.open_tags[-1]
        else:
            return self.root

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.SELF_CLOSING_TAGS:
            self.handle_endtag(tag)

    def handle_starttag(self, tag, attrs):
        attrs = normalize_attributes(attrs)
        element = Element(tag, attrs)
        self.current.append(element)
        if tag not in self.SELF_CLOSING_TAGS:
            self.open_tags.append(element)
        self.element_positions[element] = self.getpos()

    def handle_endtag(self, tag):
        if not self.open_tags:
            self.error("Unexpected end tag `%s` (%s)" % (tag, self.format_position()))
        element = self.open_tags.pop()
        while element.name != tag:
            if not self.open_tags:
                self.error(
                    "Unexpected end tag `%s` (%s)" % (tag, self.format_position())
                )
            element = self.open_tags.pop()

    def handle_data(self, data):
        self.current.append(data)


def parse_html(html):
    """
    Take a string that contains HTML and turn it into a Python object structure
    that can be easily compared against other HTML on semantic equivalence.
    Syntactical differences like which quotation is used on arguments will be
    ignored.
    """
    parser = Parser()
    parser.feed(html)
    parser.close()
    document = parser.root
    document.finalize()
    # Removing ROOT element if it's not necessary
    if len(document.children) == 1 and not isinstance(document.children[0], str):
        document = document.children[0]
    return document
