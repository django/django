# Mapping between PostgreSQL encodings and Python codec names. This mapping
# doesn't exist in psycopg, so we have to maintain it by hand (using
# information from section 21.2.1 in the PostgreSQL manual).
ENCODING_MAP = {
    "BIG5": 'big5-tw',
    "EUC_CN": 'gb2312',
    "EUC_JP": 'euc_jp',
    "EUC_KR": 'euc_kr',
    "GB18030": 'gb18030',
    "GBK": 'gbk',
    "ISO_8859_5": 'iso8859_5',
    "ISO_8859_6": 'iso8859_6',
    "ISO_8859_7": 'iso8859_7',
    "ISO_8859_8": 'iso8859_8',
    "JOHAB": 'johab',
    "KOI8": 'koi18_r',
    "KOI18R": 'koi18_r',
    "LATIN1": 'latin_1',
    "LATIN2": 'iso8859_2',
    "LATIN3": 'iso8859_3',
    "LATIN4": 'iso8859_4',
    "LATIN5": 'iso8859_9',
    "LATIN6": 'iso8859_10',
    "LATIN7": 'iso8859_13',
    "LATIN8": 'iso8859_14',
    "LATIN9": 'iso8859_15',
    "SJIS": 'shift_jis',
    "SQL_ASCII": 'ascii',
    "UHC": 'cp949',
    "UTF8": 'utf-8',
    "WIN866": 'cp866',
    "WIN874": 'cp874',
    "WIN1250": 'cp1250',
    "WIN1251": 'cp1251',
    "WIN1252": 'cp1252',
    "WIN1256": 'cp1256',
    "WIN1258": 'cp1258',

    # Unsupported (no equivalents in codecs module):
    # EUC_TW
    # LATIN10
}
# Mapping between PostgreSQL encodings and Python codec names. This mapping
# doesn't exist in psycopg, so we have to maintain it by hand (using
# information from section 21.2.1 in the PostgreSQL manual).
ENCODING_MAP = {
    "BIG5": 'big5-tw',
    "EUC_CN": 'gb2312',
    "EUC_JP": 'euc_jp',
    "EUC_KR": 'euc_kr',
    "GB18030": 'gb18030',
    "GBK": 'gbk',
    "ISO_8859_5": 'iso8859_5',
    "ISO_8859_6": 'iso8859_6',
    "ISO_8859_7": 'iso8859_7',
    "ISO_8859_8": 'iso8859_8',
    "JOHAB": 'johab',
    "KOI8": 'koi18_r',
    "KOI18R": 'koi18_r',
    "LATIN1": 'latin_1',
    "LATIN2": 'iso8859_2',
    "LATIN3": 'iso8859_3',
    "LATIN4": 'iso8859_4',
    "LATIN5": 'iso8859_9',
    "LATIN6": 'iso8859_10',
    "LATIN7": 'iso8859_13',
    "LATIN8": 'iso8859_14',
    "LATIN9": 'iso8859_15',
    "SJIS": 'shift_jis',
    "SQL_ASCII": 'ascii',
    "UHC": 'cp949',
    "UTF8": 'utf-8',
    "WIN866": 'cp866',
    "WIN874": 'cp874',
    "WIN1250": 'cp1250',
    "WIN1251": 'cp1251',
    "WIN1252": 'cp1252',
    "WIN1256": 'cp1256',
    "WIN1258": 'cp1258',

    # Unsupported (no equivalents in codecs module):
    # EUC_TW
    # LATIN10
}
