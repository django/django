from django.contrib.gis.gdal import GDAL_VERSION
from django.core.checks import Warning

W001 = Warning(
    "The installed version of GDAL does not allow blocking file and network "
    "access. Upgrade to GDAL 3.9 or higher to receive protection against "
    "malicious spatial references.",
    id="gis.W001",
    hint=f"Your version: {GDAL_VERSION}",
)


def check_gdal_39(app_configs, **kwargs):
    errors = []
    if GDAL_VERSION < (3, 9):
        errors.append(W001)
    return errors
