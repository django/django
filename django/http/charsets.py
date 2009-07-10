"Maps codec names to http1.1 charsets"

import codecs
import re
from operator import itemgetter
from django.conf import settings

_CHARSET_CODECS = {
    '437': 'cp437',
    '850': 'cp850',
    '852': 'cp852',
    '855': 'cp855',
    '857': 'cp857',
    '860': 'cp860',
    '861': 'cp861',
    '862': 'cp862',
    '863': 'cp863',
    '865': 'cp865',
    '869': 'cp869',
    'ansi_x3.4-1968': 'ascii',
    'ansi_x3.4-1986': 'ascii',
    'arabic': 'iso8859-6',
    'ascii': 'ascii',
    'asmo-708': 'iso8859-6',
    'big5': 'big5',
    'big5-hkscs': 'big5hkscs',
    'ccsid01140': 'cp1140',
    'chinese': 'gb2312',
    'cp-gr': 'cp869',
    'cp-is': 'cp861',
    'cp01140': 'cp1140',
    'cp037': 'cp037',
    'cp1026': 'cp1026',
    'cp154': 'ptcp154',
    'cp367': 'ascii',
    'cp424': 'cp424',
    'cp437': 'cp437',
    'cp500': 'cp500',
    'cp775': 'cp775',
    'cp819': 'iso8859-1',
    'cp850': 'cp850',
    'cp852': 'cp852',
    'cp855': 'cp855',
    'cp857': 'cp857',
    'cp860': 'cp860',
    'cp861': 'cp861',
    'cp862': 'cp862',
    'cp863': 'cp863',
    'cp864': 'cp864',
    'cp865': 'cp865',
    'cp869': 'cp869',
    'cp936': 'gbk',
    'csascii': 'ascii',
    'csbig5': 'big5',
    'cseuckr': 'euc_kr',
    'cseucpkdfmtjapanese': 'euc_jp',
    'csibm037': 'cp037',
    'csibm1026': 'cp1026',
    'csibm424': 'cp424',
    'csibm500': 'cp500',
    'csibm855': 'cp855',
    'csibm857': 'cp857',
    'csibm860': 'cp860',
    'csibm861': 'cp861',
    'csibm863': 'cp863',
    'csibm864': 'cp864',
    'csibm865': 'cp865',
    'csibm869': 'cp869',
    'csiso2022jp': 'iso2022_jp',
    'csiso2022jp2': 'iso2022_jp_2',
    'csiso58gb231280': 'gb2312',
    'csisolatin1': 'iso8859-1',
    'csisolatin2': 'iso8859-2',
    'csisolatin3': 'iso8859-3',
    'csisolatin4': 'iso8859-4',
    'csisolatin5': 'iso8859-9',
    'csisolatin6': 'iso8859-10',
    'csisolatinarabic': 'iso8859-6',
    'csisolatincyrillic': 'iso8859-5',
    'csisolatingreek': 'iso8859-7',
    'csisolatinhebrew': 'iso8859-8',
    'cskoi8r': 'koi8-r',
    'cspc775baltic': 'cp775',
    'cspc850multilingual': 'cp850',
    'cspc862latinhebrew': 'cp862',
    'cspc8codepage437': 'cp437',
    'cspcp852': 'cp852',
    'csptcp154': 'ptcp154',
    'csshiftjis': 'shift_jis',
    'cyrillic': 'iso8859-5',
    'cyrillic-asian': 'ptcp154',
    'ebcdic-cp-be': 'cp500',
    'ebcdic-cp-ca': 'cp037',
    'ebcdic-cp-ch': 'cp500',
    'ebcdic-cp-he': 'cp424',
    'ebcdic-cp-nl': 'cp037',
    'ebcdic-cp-us': 'cp037',
    'ebcdic-cp-wt': 'cp037',
    'ebcdic-us-37+euro': 'cp1140',
    'ecma-114': 'iso8859-6',
    'ecma-118': 'iso8859-7',
    'elot_928': 'iso8859-7',
    'euc-jp': 'euc_jp',
    'euc-kr': 'euc_kr',
    'extended_unix_code_packed_format_for_japanese': 'euc_jp',
    'gb18030': 'gb18030',
    'gb_2312-80': 'gb2312',
    'gbk': 'gbk',
    'greek': 'iso8859-7',
    'greek8': 'iso8859-7',
    'hebrew': 'iso8859-8',
    'hz-gb-2312': 'hz',
    'ibm01140': 'cp1140',
    'ibm037': 'cp037',
    'ibm1026': 'cp1026',
    'ibm367': 'ascii',
    'ibm424': 'cp424',
    'ibm437': 'cp437',
    'ibm500': 'cp500',
    'ibm775': 'cp775',
    'ibm819': 'iso8859-1',
    'ibm850': 'cp850',
    'ibm852': 'cp852',
    'ibm855': 'cp855',
    'ibm857': 'cp857',
    'ibm860': 'cp860',
    'ibm861': 'cp861',
    'ibm862': 'cp862',
    'ibm863': 'cp863',
    'ibm864': 'cp864',
    'ibm865': 'cp865',
    'ibm869': 'cp869',
    'iso-2022-jp': 'iso2022_jp',
    'iso-2022-jp-2': 'iso2022_jp_2',
    'iso-8859-1': 'iso8859-1',
    'iso-8859-10': 'iso8859-10',
    'iso-8859-13': 'iso8859-13',
    'iso-8859-14': 'iso8859-14',
    'iso-8859-15': 'iso8859-15',
    'iso-8859-2': 'iso8859-2',
    'iso-8859-3': 'iso8859-3',
    'iso-8859-4': 'iso8859-4',
    'iso-8859-5': 'iso8859-5',
    'iso-8859-6': 'iso8859-6',
    'iso-8859-7': 'iso8859-7',
    'iso-8859-8': 'iso8859-8',
    'iso-8859-9': 'iso8859-9',
    'iso-celtic': 'iso8859-14',
    'iso-ir-100': 'iso8859-1',
    'iso-ir-101': 'iso8859-2',
    'iso-ir-109': 'iso8859-3',
    'iso-ir-110': 'iso8859-4',
    'iso-ir-126': 'iso8859-7',
    'iso-ir-127': 'iso8859-6',
    'iso-ir-138': 'iso8859-8',
    'iso-ir-144': 'iso8859-5',
    'iso-ir-148': 'iso8859-9',
    'iso-ir-157': 'iso8859-10',
    'iso-ir-199': 'iso8859-14',
    'iso-ir-58': 'gb2312',
    'iso-ir-6': 'ascii',
    'iso646-us': 'ascii',
    'iso_646.irv:1991': 'ascii',
    'iso_8859-1': 'iso8859-1',
    'iso_8859-10:1992': 'iso8859-10',
    'iso_8859-14': 'iso8859-14',
    'iso_8859-14:1998': 'iso8859-14',
    'iso_8859-15': 'iso8859-15',
    'iso_8859-1:1987': 'iso8859-1',
    'iso_8859-2': 'iso8859-2',
    'iso_8859-2:1987': 'iso8859-2',
    'iso_8859-3': 'iso8859-3',
    'iso_8859-3:1988': 'iso8859-3',
    'iso_8859-4': 'iso8859-4',
    'iso_8859-4:1988': 'iso8859-4',
    'iso_8859-5': 'iso8859-5',
    'iso_8859-5:1988': 'iso8859-5',
    'iso_8859-6': 'iso8859-6',
    'iso_8859-6:1987': 'iso8859-6',
    'iso_8859-7': 'iso8859-7',
    'iso_8859-7:1987': 'iso8859-7',
    'iso_8859-8': 'iso8859-8',
    'iso_8859-8:1988': 'iso8859-8',
    'iso_8859-9': 'iso8859-9',
    'iso_8859-9:1989': 'iso8859-9',
    'koi8-r': 'koi8-r',
    'koi8-u': 'koi8-u',
    'l1': 'iso8859-1',
    'l2': 'iso8859-2',
    'l3': 'iso8859-3',
    'l4': 'iso8859-4',
    'l5': 'iso8859-9',
    'l6': 'iso8859-10',
    'l8': 'iso8859-14',
    'latin-9': 'iso8859-15',
    'latin1': 'iso8859-1',
    'latin2': 'iso8859-2',
    'latin3': 'iso8859-3',
    'latin4': 'iso8859-4',
    'latin5': 'iso8859-9',
    'latin6': 'iso8859-10',
    'latin8': 'iso8859-14',
    'ms936': 'gbk',
    'ms_kanji': 'shift_jis',
    'pt154': 'ptcp154',
    'ptcp154': 'ptcp154',
    'shift_jis': 'shift_jis',
    'us': 'ascii',
    'us-ascii': 'ascii',
    'utf-16': 'utf-16',
    'utf-16le': 'utf-16-be',
    'utf-32': 'utf-32',
    'utf-32be': 'utf-32-be',
    'utf-32le': 'utf-32-le',
    'utf-7': 'utf-7',
    'utf-8': 'utf-8',
    'windows-1250': 'cp1250',
    'windows-1251': 'cp1251',
    'windows-1252': 'cp1252',
    'windows-1253': 'cp1253',
    'windows-1254': 'cp1254',
    'windows-1255': 'cp1255',
    'windows-1256': 'cp1256',
    'windows-1257': 'cp1257',
    'windows-1258': 'cp1258',
    'windows-936': 'gbk'
}

class UnsupportedCharset(object):
    """
    Singleton class to indicate that our codec cannot be set due to an
    unsupported charset in an Accept-Charset header.
    """
    pass

def get_codec(charset):
    """
    Given the name or alias of a character set, find its Python codec if there is one.
    
    http://www.iana.org/assignments/character-sets contains valid aliases.
    The documentation for the codecs module has the list of codecs.
    
    CODEC_CHARSETS above has the codecs that correspond to character sets.
    """
    codec = None
    if charset:
        try:
            codec_name = _CHARSET_CODECS[charset.strip().lower()]
            codec = codecs.lookup(codec_name)
        except LookupError:
            # The encoding is not supported in this version of Python.
            pass
    return codec

# Returns the key for the maximum value in a dictionary
max_dict_key = lambda l:sorted(l.iteritems(), key=itemgetter(1), reverse=True)[0][0]

_CONTENT_TYPE_RE = re.compile('.*; charset=([\w\d-]+);?')
_ACCEPT_CHARSET_RE = re.compile('(?P<charset>([\w\d-]+)|(\*))(;q=(?P<q>[01](\.\d{1,3})?))?,?')
def get_response_encoding(content_type, accept_charset_header):
    """
    Searches request headers from clients and mimetype settings (which may be set 
    by users) for indicators of which charset and encoding the response should use.
    
    Attempted partial support for HTTP RFC 2616 section 14.2 and ticket 10190.
    
    Returns the highest "quality" (priority) charset that Python supports.
    
    Precedence: supported charset specified in content-type
                settings.DEFAULT_CHARSET,
                supported, "accept"ed charset such that its q > q of settings.DEFAULT_CHARSET
                iso-8859-1 if q > 0 or is unspecified
                406 error
            
    """
    used_content_type = False
    charset = None
    codec = None
    # Try to get the codec from a content-type, verify that the charset is valid.
    if content_type:
        match = _CONTENT_TYPE_RE.match(content_type)
        if match:
            charset = match.group(1)
            codec = get_codec(charset)
            if not codec:   # Unsupported charset
                raise Exception("Unsupported charset in Content-Type header.")
        else:
            charset = settings.DEFAULT_CHARSET
        used_content_type = True

    # Handle Accept-Charset (only if we have not gotten one with content_type).
    if not used_content_type:
        if not accept_charset_header: # No information to find a charset with.
            return None, None

        # Get list of matches for Accepted-Charsets.
        # [{ charset : q }, { charset : q }]
        match_iterator = _ACCEPT_CHARSET_RE.finditer(accept_charset_header)
        accept_charset = [m.groupdict() for m in match_iterator]

        # Remove charsets we cannot encode and whose q values are 0
        charsets = _process_accept_charset(accept_charset)

        # Establish the prioritized charsets (ones we know about beforehand)
        default_charset = settings.DEFAULT_CHARSET
        fallback_charset = "ISO-8859-1"

        # Prefer default_charset if its q value is 1 or we have no valid acceptable charsets.
        max_q_charset = max_dict_key(charsets)
        max_q_value = charsets[max_q_charset]
        if max_q_value == 0:
            if fallback_charset not in charsets or charsets[fallback_charset] > 0:
                charset = fallback_charset
        elif charsets[default_charset] == 1 or charsets[default_charset] == max_q_value:
            charset = default_charset
        # Get the highest valued acceptable charset (if we aren't going to the fallback
        # or defaulting)
        else:
            charset = max_q_charset

    codec = get_codec(charset)

    # We may reach here with no codec or no charset. We will change the status 
    # code in the HttpResponse.
    return charset, codec

# NOTE -- make sure we are not duping the processing of q values
def _process_accept_charset(accept_charset):
    '''
    HTTP RFC 2616 section 14.2 dictates that q must be between 0 and 1.
    This method normalizes charset quality values, cleans whitespace from charset
    names, and excludes charsets without Python codecs and whose q values are 0.
    '''
    accepted_charsets = {}

    default_value = 1
    wildcard = False

    for potential in accept_charset:
        charset = potential["charset"].strip()            
        # The default quality value is 1
        if not potential["q"]:
            q = 1.
        else:    
            q = float(potential["q"])
        # Exclude unsupported charsets (those without codecs in Python)
        if get_codec(charset) and q >= 0 and q <= 1:
            accepted_charsets[charset] = q
        elif charset == "*" and q >= 0 and q <= 1:
            default_value = q
            wildcard = True

    if settings.DEFAULT_CHARSET not in accepted_charsets:
        accepted_charsets[settings.DEFAULT_CHARSET] = default_value 
    if "ISO-8859-1" not in accepted_charsets and wildcard: 
        accepted_charsets["ISO-8859-1"] = default_value

    return accepted_charsets
