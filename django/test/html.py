"""Compare two HTML documents."""

from html.parser import HTMLParser

from django.utils.regex_helper import _lazy_re_compile

# ASCII whitespace is U+0009 TAB, U+000A LF, U+000C FF, U+000D CR, or U+0020
# SPACE.
# https://infra.spec.whatwg.org/#ascii-whitespace
ASCII_WHITESPACE = _lazy_re_compile(r'[\t\n\f\r ]+')


def normalize_whitespace(string):
    return ASCII_WHITESPACE.sub(' ', string)


class Element:
    def __init__(self, name, attributes):
        self.name = name
        self.attributes = sorted(attributes)
        self.children = []

    def append(self, element):
        if isinstance(element, str):
            element = normalize_whitespace(element)
            if self.children:
                if isinstance(self.children[-1], str):
                    self.children[-1] += element
                    self.children[-1] = normalize_whitespace(self.children[-1])
                    return
        elif self.children:
            # removing last children if it is only whitespace
            # this can result in incorrect dom representations since
            # whitespace between inline tags like <span> is significant
            if isinstance(self.children[-1], str):
                if self.children[-1].isspace():
                    self.children.pop()
        if element:
            self.children.append(element)

    def finalize(self):
        def rstrip_last_element(children):
            if children:
                if isinstance(children[-1], str):
                    children[-1] = children[-1].rstrip()
                    if not children[-1]:
                        children.pop()
                        children = rstrip_last_element(children)
            return children

        rstrip_last_element(self.children)
        for i, child in enumerate(self.children):
            if isinstance(child, str):
                self.children[i] = child.strip()
            elif hasattr(child, 'finalize'):
                child.finalize()

    def __eq__(self, element):
        if not hasattr(element, 'name') or self.name != element.name:
            return False
        if len(self.attributes) != len(element.attributes):
            return False
        if self.attributes != element.attributes:
            # attributes without a value is same as attribute with value that
            # equals the attributes name:
            # <input checked> == <input checked="checked">
            for i in range(len(self.attributes)):
                attr, value = self.attributes[i]
                other_attr, other_value = element.attributes[i]
                if value is None:
                    value = attr
                if other_value is None:
                    other_value = other_attr
                if attr != other_attr or value != other_value:
                    return False
        return self.children == element.children

    def __hash__(self):
        return hash((self.name, *self.attributes))

    def _count(self, element, count=True):
        if not isinstance(element, str):
            if self == element:
                return 1
        if isinstance(element, RootElement):
            if self.children == element.children:
                return 1
        i = 0
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
                i += child._count(element, count=count)
                if not count and i:
                    return i
        return i

    def __contains__(self, element):
        return self._count(element, count=False) > 0

    def count(self, element):
        return self._count(element, count=True)

    def __getitem__(self, key):
        return self.children[key]

    def __str__(self):
        output = '<%s' % self.name
        for key, value in self.attributes:
            if value:
                output += ' %s="%s"' % (key, value)
            else:
                output += ' %s' % key
        if self.children:
            output += '>\n'
            output += ''.join(str(c) for c in self.children)
            output += '\n</%s>' % self.name
        else:
            output += '>'
        return output

    def __repr__(self):
        return str(self)


class RootElement(Element):
    def __init__(self):
        super().__init__(None, ())

    def __str__(self):
        return ''.join(str(c) for c in self.children)


class HTMLParseError(Exception):
    pass


class Parser(HTMLParser):
    # https://html.spec.whatwg.org/#void-elements
    SELF_CLOSING_TAGS = {
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta',
        'param', 'source', 'track', 'wbr',
        # Deprecated tags
        'frame', 'spacer',
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
        if hasattr(position, 'lineno'):
            position = position.lineno, position.offset
        return 'Line %d, Column %d' % position

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
        # Special case handling of 'class' attribute, so that comparisons of DOM
        # instances are not sensitive to ordering of classes.
        attrs = [
            (name, ' '.join(sorted(value for value in ASCII_WHITESPACE.split(value) if value)))
            if name == "class"
            else (name, value)
            for name, value in attrs
        ]
        element = Element(tag, attrs)
        self.current.append(element)
        if tag not in self.SELF_CLOSING_TAGS:
            self.open_tags.append(element)
        self.element_positions[element] = self.getpos()

    def handle_endtag(self, tag):
        if not self.open_tags:
            self.error("Unexpected end tag `%s` (%s)" % (
                tag, self.format_position()))
        element = self.open_tags.pop()
        while element.name != tag:
            if not self.open_tags:
                self.error("Unexpected end tag `%s` (%s)" % (
                    tag, self.format_position()))
            element = self.open_tags.pop()

    def handle_data(self, data):
        self.current.append(data)


def parse_html(html):
    """
    Take a string that contains *valid* HTML and turn it into a Python object
    structure that can be easily compared against other HTML on semantic
    equivalence. Syntactical differences like which quotation is used on
    arguments will be ignored.
    """
    parser = Parser()
    parser.feed(html)
    parser.close()
    document = parser.root
    document.finalize()
    # Removing ROOT element if it's not necessary
    if len(document.children) == 1:
        if not isinstance(document.children[0], str):
            document = document.children[0]
    return document
