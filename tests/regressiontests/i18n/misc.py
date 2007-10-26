tests = """
>>> from django.utils.translation.trans_real import parse_accept_lang_header
>>> p = parse_accept_lang_header

Good headers.
>>> p('de')
[('de', 1.0)]
>>> p('en-AU')
[('en-AU', 1.0)]
>>> p('*;q=1.00')
[('*', 1.0)]
>>> p('en-AU;q=0.123')
[('en-AU', 0.123)]
>>> p('en-au;q=0.1')
[('en-au', 0.10000000000000001)]
>>> p('en-au;q=1.0')
[('en-au', 1.0)]
>>> p('da, en-gb;q=0.25, en;q=0.5')
[('da', 1.0), ('en', 0.5), ('en-gb', 0.25)]
>>> p('en-au-xx')
[('en-au-xx', 1.0)]
>>> p('de,en-au;q=0.75,en-us;q=0.5,en;q=0.25,es;q=0.125,fa;q=0.125')
[('de', 1.0), ('en-au', 0.75), ('en-us', 0.5), ('en', 0.25), ('es', 0.125), ('fa', 0.125)]
>>> p('*')
[('*', 1.0)]
>>> p('de;q=0.')
[('de', 1.0)]
>>> p('')
[]

Bad headers; should always return [].
>>> p('en-gb;q=1.0000')
[]
>>> p('en;q=0.1234')
[]
>>> p('en;q=.2')
[]
>>> p('abcdefghi-au')
[]
>>> p('**')
[]
>>> p('en,,gb')
[]
>>> p('en-au;q=0.1.0')
[]
>>> p('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXZ,en')
[]
>>> p('da, en-gb;q=0.8, en;q=0.7,#')
[]
>>> p('de;q=2.0')
[]
>>> p('de;q=0.a')
[]
>>> p('')
[]

"""
