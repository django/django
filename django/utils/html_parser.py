import html.parser

try:
    HTMLParseError = html.parser.HTMLParseError
except AttributeError:
    # create a dummy class for Python 3.5+ where it's been removed
    class HTMLParseError(Exception):
        pass


class HTMLParser(html.parser.HTMLParser):
    """Explicitly set convert_charrefs to be False.

    This silences a deprecation warning on Python 3.4.
    """
    def __init__(self, convert_charrefs=False, **kwargs):
        html.parser.HTMLParser.__init__(self, convert_charrefs=convert_charrefs, **kwargs)
