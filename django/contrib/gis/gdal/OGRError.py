# OGR Error Codes
OGRERR_NONE = 0
OGRERR_NOT_ENOUGH_DATA = 1
OGRERR_NOT_ENOUGH_MEMORY = 2
OGRERR_UNSUPPORTED_GEOMETRY_TYPE = 3
OGRERR_UNSUPPORTED_OPERATION = 4
OGRERR_CORRUPT_DATA = 5
OGRERR_FAILURE = 6
OGRERR_UNSUPPORTED_SRS = 7

# OGR & SRS Exceptions
class OGRException(Exception): pass
class SRSException(Exception): pass

def check_err(code, msg=False):
    "Checks the given OGRERR, and raises an exception where appropriate."

    if code == OGRERR_NONE:
        return
    elif code == OGRERR_NOT_ENOUGH_DATA:
        raise OGRException, 'Not enough data!'
    elif code == OGRERR_NOT_ENOUGH_MEMORY:
        raise OGRException, 'Not enough memory!'
    elif code == OGRERR_UNSUPPORTED_GEOMETRY_TYPE:
        raise OGRException, 'Unsupported Geometry Type!'
    elif code == OGRERR_UNSUPPORTED_OPERATION:
        raise OGRException, 'Unsupported Operation!'
    elif code == OGRERR_CORRUPT_DATA:
        raise OGRException, 'Corrupt Data!'
    elif code == OGRERR_FAILURE:
        raise OGRException, 'OGR Failure!'
    elif code == OGRERR_UNSUPPORTED_SRS:
        raise SRSException, 'Unsupported SRS!'
    else:
        raise OGRException, 'Unknown error code: "%s"' % str(code)
