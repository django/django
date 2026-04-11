from cpython.bytes cimport PyBytes_FromStringAndSize
from cpython.exc cimport PyErr_NoMemory
from cpython.mem cimport PyMem_Free, PyMem_Malloc, PyMem_Realloc
from cpython.object cimport PyObject_Str
from libc.stdint cimport uint8_t, uint64_t
from libc.string cimport memcpy

from multidict import istr

DEF BUF_SIZE = 16 * 1024  # 16KiB

cdef object _istr = istr


# ----------------- writer ---------------------------

cdef struct Writer:
    char *buf
    Py_ssize_t size
    Py_ssize_t pos
    bint heap_allocated

cdef inline void _init_writer(Writer* writer, char *buf):
    writer.buf = buf
    writer.size = BUF_SIZE
    writer.pos = 0
    writer.heap_allocated = 0


cdef inline void _release_writer(Writer* writer):
    if writer.heap_allocated:
        PyMem_Free(writer.buf)


cdef inline int _write_byte(Writer* writer, uint8_t ch):
    cdef char * buf
    cdef Py_ssize_t size

    if writer.pos == writer.size:
        # reallocate
        size = writer.size + BUF_SIZE
        if not writer.heap_allocated:
            buf = <char*>PyMem_Malloc(size)
            if buf == NULL:
                PyErr_NoMemory()
                return -1
            memcpy(buf, writer.buf, writer.size)
        else:
            buf = <char*>PyMem_Realloc(writer.buf, size)
            if buf == NULL:
                PyErr_NoMemory()
                return -1
        writer.buf = buf
        writer.size = size
        writer.heap_allocated = 1
    writer.buf[writer.pos] = <char>ch
    writer.pos += 1
    return 0


cdef inline int _write_utf8(Writer* writer, Py_UCS4 symbol):
    cdef uint64_t utf = <uint64_t> symbol

    if utf < 0x80:
        return _write_byte(writer, <uint8_t>utf)
    elif utf < 0x800:
        if _write_byte(writer, <uint8_t>(0xc0 | (utf >> 6))) < 0:
            return -1
        return _write_byte(writer,  <uint8_t>(0x80 | (utf & 0x3f)))
    elif 0xD800 <= utf <= 0xDFFF:
        # surogate pair, ignored
        return 0
    elif utf < 0x10000:
        if _write_byte(writer, <uint8_t>(0xe0 | (utf >> 12))) < 0:
            return -1
        if _write_byte(writer, <uint8_t>(0x80 | ((utf >> 6) & 0x3f))) < 0:
            return -1
        return _write_byte(writer, <uint8_t>(0x80 | (utf & 0x3f)))
    elif utf > 0x10FFFF:
        # symbol is too large
        return 0
    else:
        if _write_byte(writer,  <uint8_t>(0xf0 | (utf >> 18))) < 0:
            return -1
        if _write_byte(writer,
                       <uint8_t>(0x80 | ((utf >> 12) & 0x3f))) < 0:
           return -1
        if _write_byte(writer,
                       <uint8_t>(0x80 | ((utf >> 6) & 0x3f))) < 0:
            return -1
        return _write_byte(writer, <uint8_t>(0x80 | (utf & 0x3f)))


cdef inline int _write_str(Writer* writer, str s):
    cdef Py_UCS4 ch
    for ch in s:
        if _write_utf8(writer, ch) < 0:
            return -1


cdef inline int _write_str_raise_on_nlcr(Writer* writer, object s):
    cdef Py_UCS4 ch
    cdef str out_str
    if type(s) is str:
        out_str = <str>s
    elif type(s) is _istr:
        out_str = PyObject_Str(s)
    elif not isinstance(s, str):
        raise TypeError("Cannot serialize non-str key {!r}".format(s))
    else:
        out_str = str(s)

    for ch in out_str:
        if ch == 0x0D or ch == 0x0A:
            raise ValueError(
                "Newline or carriage return detected in headers. "
                "Potential header injection attack."
            )
        if _write_utf8(writer, ch) < 0:
            return -1


# --------------- _serialize_headers ----------------------

def _serialize_headers(str status_line, headers):
    cdef Writer writer
    cdef object key
    cdef object val
    cdef char buf[BUF_SIZE]

    _init_writer(&writer, buf)

    try:
        if _write_str(&writer, status_line) < 0:
            raise
        if _write_byte(&writer, b'\r') < 0:
            raise
        if _write_byte(&writer, b'\n') < 0:
            raise

        for key, val in headers.items():
            if _write_str_raise_on_nlcr(&writer, key) < 0:
                raise
            if _write_byte(&writer, b':') < 0:
                raise
            if _write_byte(&writer, b' ') < 0:
                raise
            if _write_str_raise_on_nlcr(&writer, val) < 0:
                raise
            if _write_byte(&writer, b'\r') < 0:
                raise
            if _write_byte(&writer, b'\n') < 0:
                raise

        if _write_byte(&writer, b'\r') < 0:
            raise
        if _write_byte(&writer, b'\n') < 0:
            raise

        return PyBytes_FromStringAndSize(writer.buf, writer.pos)
    finally:
        _release_writer(&writer)
