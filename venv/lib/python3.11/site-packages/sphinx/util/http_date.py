"""Convert times to and from HTTP-date serialisations.

Reference: https://www.rfc-editor.org/rfc/rfc7231#section-7.1.1.1
"""

import time
import warnings
from email.utils import formatdate, parsedate_tz

from sphinx.deprecation import RemovedInSphinx90Warning

_GMT_OFFSET = float(time.localtime().tm_gmtoff)


def epoch_to_rfc1123(epoch: float) -> str:
    """Return HTTP-date string from epoch offset."""
    return formatdate(epoch, usegmt=True)


def rfc1123_to_epoch(rfc1123: str) -> float:
    """Return epoch offset from HTTP-date string."""
    t = parsedate_tz(rfc1123)
    if t is None:
        raise ValueError
    if not rfc1123.endswith(" GMT"):
        warnings.warn(
            "HTTP-date string does not meet RFC 7231 requirements "
            f"(must end with 'GMT'): {rfc1123!r}",
            RemovedInSphinx90Warning, stacklevel=3,
        )
    epoch_secs = time.mktime(time.struct_time(t[:9])) + _GMT_OFFSET
    if (gmt_offset := t[9]) != 0:
        warnings.warn(
            "HTTP-date string does not meet RFC 7231 requirements "
            f"(must be GMT time): {rfc1123!r}",
            RemovedInSphinx90Warning, stacklevel=3,
        )
        return epoch_secs - (gmt_offset or 0)
    return epoch_secs
