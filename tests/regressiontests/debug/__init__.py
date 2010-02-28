# -*- coding: utf8 -*-

class BrokenException(Exception):
    pass

except_args = ('Broken!',           # plain exception with ASCII text
               u'¡Broken!',        # non-ASCII unicode data
               '¡Broken!',         # non-ASCII, utf-8 encoded bytestring
               '\xa1Broken!', )     # non-ASCII, latin1 bytestring

