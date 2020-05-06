import struct

from django.core.exceptions import ValidationError

from .const import (
    BANDTYPE_FLAG_HASNODATA, BANDTYPE_PIXTYPE_MASK, GDAL_TO_POSTGIS,
    GDAL_TO_STRUCT, POSTGIS_HEADER_STRUCTURE, POSTGIS_TO_GDAL, STRUCT_SIZE,
)


def pack(structure, data):
    """
    Pack data into hex string with little endian format.
    """
    return struct.pack('<' + structure, *data)


def unpack(structure, data):
    """
    Unpack little endian hexlified binary string into a list.
    """
    return struct.unpack('<' + structure, bytes.fromhex(data))


def chunk(data, index):
    """
    Split a string into two parts at the input index.
    """
    return data[:index], data[index:]


def from_pgraster(data):
    """
    Convert a PostGIS HEX String into a dictionary.
    """
    if data is None:
        return

    # Split raster header from data
    header, data = chunk(data, 122)
    header = unpack(POSTGIS_HEADER_STRUCTURE, header)

    # Parse band data
    bands = []
    pixeltypes = []
    while data:
        # Get pixel type for this band
        pixeltype_with_flags, data = chunk(data, 2)
        pixeltype_with_flags = unpack('B', pixeltype_with_flags)[0]
        pixeltype = pixeltype_with_flags & BANDTYPE_PIXTYPE_MASK

        # Convert datatype from PostGIS to GDAL & get pack type and size
        pixeltype = POSTGIS_TO_GDAL[pixeltype]
        pack_type = GDAL_TO_STRUCT[pixeltype]
        pack_size = 2 * STRUCT_SIZE[pack_type]

        # Parse band nodata value. The nodata value is part of the
        # PGRaster string even if the nodata flag is True, so it always
        # has to be chunked off the data string.
        nodata, data = chunk(data, pack_size)
        nodata = unpack(pack_type, nodata)[0]

        # Chunk and unpack band data (pack size times nr of pixels)
        band, data = chunk(data, pack_size * header[10] * header[11])
        band_result = {'data': bytes.fromhex(band)}

        # Set the nodata value if the nodata flag is set.
        if pixeltype_with_flags & BANDTYPE_FLAG_HASNODATA:
            band_result['nodata_value'] = nodata

        # Append band data to band list
        bands.append(band_result)

        # Store pixeltype of this band in pixeltypes array
        pixeltypes.append(pixeltype)

    # Check that all bands have the same pixeltype.
    # This is required by GDAL. PostGIS rasters could have different pixeltypes
    # for bands of the same raster.
    if len(set(pixeltypes)) != 1:
        raise ValidationError("Band pixeltypes are not all equal.")

    return {
        'srid': int(header[9]),
        'width': header[10], 'height': header[11],
        'datatype': pixeltypes[0],
        'origin': (header[5], header[6]),
        'scale': (header[3], header[4]),
        'skew': (header[7], header[8]),
        'bands': bands,
    }


def to_pgraster(rast):
    """
    Convert a GDALRaster into PostGIS Raster format.
    """
    # Prepare the raster header data as a tuple. The first two numbers are
    # the endianness and the PostGIS Raster Version, both are fixed by
    # PostGIS at the moment.
    rasterheader = (
        1, 0, len(rast.bands), rast.scale.x, rast.scale.y,
        rast.origin.x, rast.origin.y, rast.skew.x, rast.skew.y,
        rast.srs.srid, rast.width, rast.height,
    )

    # Pack raster header.
    result = pack(POSTGIS_HEADER_STRUCTURE, rasterheader)

    for band in rast.bands:
        # The PostGIS raster band header has exactly two elements, a 8BUI byte
        # and the nodata value.
        #
        # The 8BUI stores both the PostGIS pixel data type and a nodata flag.
        # It is composed as the datatype with BANDTYPE_FLAG_HASNODATA (1 << 6)
        # for existing nodata values:
        #   8BUI_VALUE = PG_PIXEL_TYPE (0-11) | BANDTYPE_FLAG_HASNODATA
        #
        # For example, if the byte value is 71, then the datatype is
        #   71 & ~BANDTYPE_FLAG_HASNODATA = 7 (32BSI)
        # and the nodata value is True.
        structure = 'B' + GDAL_TO_STRUCT[band.datatype()]

        # Get band pixel type in PostGIS notation
        pixeltype = GDAL_TO_POSTGIS[band.datatype()]

        # Set the nodata flag
        if band.nodata_value is not None:
            pixeltype |= BANDTYPE_FLAG_HASNODATA

        # Pack band header
        bandheader = pack(structure, (pixeltype, band.nodata_value or 0))

        # Add packed header and band data to result
        result += bandheader + band.data(as_memoryview=True)

    # Convert raster to hex string before passing it to the DB.
    return result.hex()
