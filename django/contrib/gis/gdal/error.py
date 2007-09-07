"""
  This module houses the OGR & SRS Exception objects, and the
   check_err() routine which checks the status code returned by
   OGR methods.
"""

# OGR & SRS Exceptions
class OGRException(Exception): pass
class SRSException(Exception): pass

# OGR Error Codes
OGRERR_DICT = { 1 : (OGRException, 'Not enough data.'),
                2 : (OGRException, 'Not enough memory.'),
                3 : (OGRException, 'Unsupported geometry type.'),
                4 : (OGRException, 'Unsupported operation.'),
                5 : (OGRException, 'Corrupt data.'),
                6 : (OGRException, 'OGR failure.'),
                7 : (SRSException, 'Unsupported SRS.'),
                }
OGRERR_NONE = 0

def check_err(code):
    "Checks the given OGRERR, and raises an exception where appropriate."
    
    if code == OGRERR_NONE:
        return
    elif code in OGRERR_DICT:
        e, msg = OGRERR_DICT[code]
        raise e, msg
    else:
        raise OGRException, 'Unknown error code: "%s"' % code
