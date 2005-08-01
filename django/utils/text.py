import re

# Capitalizes the first letter of a string.
capfirst = lambda x: x and x[0].upper() + x[1:]

def wrap(text, width):
    """
    A word-wrap function that preserves existing line breaks and most spaces in
    the text. Expects that existing line breaks are posix newlines (\n).
    See http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/148061
    """
    return reduce(lambda line, word, width=width: '%s%s%s' %
                  (line,
                   ' \n'[(len(line[line.rfind('\n')+1:])
                         + len(word.split('\n',1)[0]
                              ) >= width)],
                   word),
                  text.split(' ')
                 )

def truncate_words(s, num):
    "Truncates a string after a certain number of words."
    length = int(num)
    words = s.split()
    if len(words) > length:
        words = words[:length]
        if not words[-1].endswith('...'):
            words.append('...')
    return ' '.join(words)

def get_valid_filename(s):
    """
    Returns the given string converted to a string that can be used for a clean
    filename. Specifically, leading and trailing spaces are removed; other
    spaces are converted to underscores; and all non-filename-safe characters
    are removed.
    >>> get_valid_filename("john's portrait in 2004.jpg")
    'johns_portrait_in_2004.jpg'
    """
    s = s.strip().replace(' ', '_')
    return re.sub(r'[^-A-Za-z0-9_.]', '', s)

def fix_microsoft_characters(s):
    """
    Converts Microsoft proprietary characters (e.g. smart quotes, em-dashes)
    to sane characters
    """
    # Sources:
    # http://stsdas.stsci.edu/bps/pythontalk8.html
    # http://www.waider.ie/hacks/workshop/perl/rss-fetch.pl
    # http://www.fourmilab.ch/webtools/demoroniser/
    return s
    s = s.replace('\x91', "'")
    s = s.replace('\x92', "'")
    s = s.replace('\x93', '"')
    s = s.replace('\x94', '"')
    s = s.replace('\xd2', '"')
    s = s.replace('\xd3', '"')
    s = s.replace('\xd5', "'")
    s = s.replace('\xad', '--')
    s = s.replace('\xd0', '--')
    s = s.replace('\xd1', '--')
    s = s.replace('\xe2\x80\x98', "'") # weird single quote (open)
    s = s.replace('\xe2\x80\x99', "'") # weird single quote (close)
    s = s.replace('\xe2\x80\x9c', '"') # weird double quote (open)
    s = s.replace('\xe2\x80\x9d', '"') # weird double quote (close)
    s = s.replace('\xe2\x81\x84', '/')
    s = s.replace('\xe2\x80\xa6', '...')
    s = s.replace('\xe2\x80\x94', '--')
    return s

def get_text_list(list_, last_word='or'):
    """
    >>> get_text_list(['a', 'b', 'c', 'd'])
    'a, b, c or d'
    >>> get_text_list(['a', 'b', 'c'], 'and')
    'a, b and c'
    >>> get_text_list(['a', 'b'], 'and')
    'a and b'
    >>> get_text_list(['a'])
    'a'
    >>> get_text_list([])
    ''
    """
    if len(list_) == 0: return ''
    if len(list_) == 1: return list_[0]
    return '%s %s %s' % (', '.join([i for i in list_][:-1]), last_word, list_[-1])

def normalize_newlines(text):
    return re.sub(r'\r\n|\r|\n', '\n', text)

def recapitalize(text):
    "Recapitalizes text, placing caps after end-of-sentence punctuation."
    capwords = 'I Jayhawk Jayhawks Lawrence Kansas KS'.split()
    text = text.lower()
    capsRE = re.compile(r'(?:^|(?<=[\.\?\!] ))([a-z])')
    text = capsRE.sub(lambda x: x.group(1).upper(), text)
    for capword in capwords:
        capwordRE = re.compile(r'\b%s\b' % capword, re.I)
        text = capwordRE.sub(capword, text)
    return text

def phone2numeric(phone):
    "Converts a phone number with letters into its numeric equivalent."
    letters = re.compile(r'[A-PR-Y]', re.I)
    char2number = lambda m: {'a': '2', 'c': '2', 'b': '2', 'e': '3',
         'd': '3', 'g': '4', 'f': '3', 'i': '4', 'h': '4', 'k': '5',
         'j': '5', 'm': '6', 'l': '5', 'o': '6', 'n': '6', 'p': '7',
         's': '7', 'r': '7', 'u': '8', 't': '8', 'w': '9', 'v': '8',
         'y': '9', 'x': '9'}.get(m.group(0).lower())
    return letters.sub(char2number, phone)

# From http://www.xhaus.com/alan/python/httpcomp.html#gzip
# Used with permission.
def compress_string(s):
    import cStringIO, gzip
    zbuf = cStringIO.StringIO()
    zfile = gzip.GzipFile(mode='wb', compresslevel=6, fileobj=zbuf)
    zfile.write(s)
    zfile.close()
    return zbuf.getvalue()
