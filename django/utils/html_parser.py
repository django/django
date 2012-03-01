import HTMLParser as _HTMLParser
import re


class HTMLParser(_HTMLParser.HTMLParser):
    """
    Patched version of stdlib's HTMLParser with patch from:
    http://bugs.python.org/issue670664
    """
    def __init__(self):
        _HTMLParser.HTMLParser.__init__(self)
        self.cdata_tag = None

    def set_cdata_mode(self, tag):
        try:
            self.interesting = _HTMLParser.interesting_cdata
        except AttributeError:
            self.interesting = re.compile(r'</\s*%s\s*>' % tag.lower(), re.I)
        self.cdata_tag = tag.lower()

    def clear_cdata_mode(self):
        self.interesting = _HTMLParser.interesting_normal
        self.cdata_tag = None

    # Internal -- handle starttag, return end or -1 if not terminated
    def parse_starttag(self, i):
        self.__starttag_text = None
        endpos = self.check_for_whole_start_tag(i)
        if endpos < 0:
            return endpos
        rawdata = self.rawdata
        self.__starttag_text = rawdata[i:endpos]

        # Now parse the data between i+1 and j into a tag and attrs
        attrs = []
        match = _HTMLParser.tagfind.match(rawdata, i + 1)
        assert match, 'unexpected call to parse_starttag()'
        k = match.end()
        self.lasttag = tag = rawdata[i + 1:k].lower()

        while k < endpos:
            m = _HTMLParser.attrfind.match(rawdata, k)
            if not m:
                break
            attrname, rest, attrvalue = m.group(1, 2, 3)
            if not rest:
                attrvalue = None
            elif attrvalue[:1] == '\'' == attrvalue[-1:] or \
                 attrvalue[:1] == '"' == attrvalue[-1:]:
                attrvalue = attrvalue[1:-1]
                attrvalue = self.unescape(attrvalue)
            attrs.append((attrname.lower(), attrvalue))
            k = m.end()

        end = rawdata[k:endpos].strip()
        if end not in (">", "/>"):
            lineno, offset = self.getpos()
            if "\n" in self.__starttag_text:
                lineno = lineno + self.__starttag_text.count("\n")
                offset = len(self.__starttag_text) \
                         - self.__starttag_text.rfind("\n")
            else:
                offset = offset + len(self.__starttag_text)
            self.error("junk characters in start tag: %r"
                       % (rawdata[k:endpos][:20],))
        if end.endswith('/>'):
            # XHTML-style empty tag: <span attr="value" />
            self.handle_startendtag(tag, attrs)
        else:
            self.handle_starttag(tag, attrs)
            if tag in self.CDATA_CONTENT_ELEMENTS:
                self.set_cdata_mode(tag) # <--------------------------- Changed
        return endpos

    # Internal -- parse endtag, return end or -1 if incomplete
    def parse_endtag(self, i):
        rawdata = self.rawdata
        assert rawdata[i:i + 2] == "</", "unexpected call to parse_endtag"
        match = _HTMLParser.endendtag.search(rawdata, i + 1) # >
        if not match:
            return -1
        j = match.end()
        match = _HTMLParser.endtagfind.match(rawdata, i) # </ + tag + >
        if not match:
            if self.cdata_tag is not None: # *** add ***
                self.handle_data(rawdata[i:j]) # *** add ***
                return j # *** add ***
            self.error("bad end tag: %r" % (rawdata[i:j],))
        # --- changed start ---------------------------------------------------
        tag = match.group(1).strip()
        if self.cdata_tag is not None:
            if tag.lower() != self.cdata_tag:
                self.handle_data(rawdata[i:j])
                return j
        # --- changed end -----------------------------------------------------
        self.handle_endtag(tag.lower())
        self.clear_cdata_mode()
        return j
