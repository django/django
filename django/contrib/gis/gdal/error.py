"""
 This module houses the GDAL & SRS Exception objects, and the
 check_err() routine which checks the status code returned by
 GDAL/OGR methods.
"""


# #### GDAL & SRS Exceptions ####
class GDALException(Exception):
    pass


class SRSException(Exception):
    pass


# #### GDAL/OGR error checking codes and routine ####

# OGR Error Codes
OGRERR_DICT = {
    1: (GDALException, 'Not enough data.'),
    2: (GDALException, 'Not enough memory.'),
    3: (GDALException, 'Unsupported geometry type.'),
    4: (GDALException, 'Unsupported operation.'),
    5: (GDALException, 'Corrupt data.'),
    6: (GDALException, 'OGR failure.'),
    7: (SRSException, 'Unsupported SRS.'),
    8: (GDALException, 'Invalid handle.'),
}

# CPL Error Codes
# https://www.gdal.org/cpl__error_8h.html
CPLERR_DICT = {
    1: (GDALException, 'AppDefined'),
    2: (GDALException, 'OutOfMemory'),
    3: (GDALException, 'FileIO'),
    4: (GDALException, 'OpenFailed'),
    5: (GDALException, 'IllegalArg'),
    6: (GDALException, 'NotSupported'),
    7: (GDALException, 'AssertionFailed'),
    8: (GDALException, 'NoWriteAccess'),
    9: (GDALException, 'UserInterrupt'),
    10: (GDALException, 'ObjectNull'),
}

ERR_NONE = 0


def check_err(code, cpl=False):
    """
    Check the given CPL/OGRERR and raise an exception where appropriate.
    """
    err_dict = CPLERR_DICT if cpl else OGRERR_DICT

    if code == ERR_NONE:
        return
    elif code in err_dict:
        e, msg = err_dict[code]
        raise e(msg)
    else:
        raise GDALException('Unknown error code: "%s"' % code)
