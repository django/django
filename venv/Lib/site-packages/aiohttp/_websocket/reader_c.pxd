import cython

from .mask cimport _websocket_mask_cython as websocket_mask


cdef unsigned int READ_HEADER
cdef unsigned int READ_PAYLOAD_LENGTH
cdef unsigned int READ_PAYLOAD_MASK
cdef unsigned int READ_PAYLOAD

cdef int OP_CODE_NOT_SET
cdef int OP_CODE_CONTINUATION
cdef int OP_CODE_TEXT
cdef int OP_CODE_BINARY
cdef int OP_CODE_CLOSE
cdef int OP_CODE_PING
cdef int OP_CODE_PONG

cdef int COMPRESSED_NOT_SET
cdef int COMPRESSED_FALSE
cdef int COMPRESSED_TRUE

cdef object UNPACK_LEN3
cdef object UNPACK_CLOSE_CODE
cdef object TUPLE_NEW

cdef object WSMsgType
cdef object WSMessage

cdef object WS_MSG_TYPE_TEXT
cdef object WS_MSG_TYPE_BINARY

cdef set ALLOWED_CLOSE_CODES
cdef set MESSAGE_TYPES_WITH_CONTENT

cdef tuple EMPTY_FRAME
cdef tuple EMPTY_FRAME_ERROR

cdef class WebSocketDataQueue:

    cdef unsigned int _size
    cdef public object _protocol
    cdef unsigned int _limit
    cdef object _loop
    cdef bint _eof
    cdef object _waiter
    cdef object _exception
    cdef public object _buffer
    cdef object _get_buffer
    cdef object _put_buffer

    cdef void _release_waiter(self)

    cpdef void feed_data(self, object data, unsigned int size)

    @cython.locals(size="unsigned int")
    cdef _read_from_buffer(self)

cdef class WebSocketReader:

    cdef WebSocketDataQueue queue
    cdef unsigned int _max_msg_size

    cdef Exception _exc
    cdef bytearray _partial
    cdef unsigned int _state

    cdef int _opcode
    cdef bint _frame_fin
    cdef int _frame_opcode
    cdef list _payload_fragments
    cdef Py_ssize_t _frame_payload_len

    cdef bytes _tail
    cdef bint _has_mask
    cdef bytes _frame_mask
    cdef Py_ssize_t _payload_bytes_to_read
    cdef unsigned int _payload_len_flag
    cdef int _compressed
    cdef object _decompressobj
    cdef bint _compress

    cpdef tuple feed_data(self, object data)

    @cython.locals(
        is_continuation=bint,
        fin=bint,
        has_partial=bint,
        payload_merged=bytes,
    )
    cpdef void _handle_frame(self, bint fin, int opcode, object payload, int compressed) except *

    @cython.locals(
        start_pos=Py_ssize_t,
        data_len=Py_ssize_t,
        length=Py_ssize_t,
        chunk_size=Py_ssize_t,
        chunk_len=Py_ssize_t,
        data_len=Py_ssize_t,
        data_cstr="const unsigned char *",
        first_byte="unsigned char",
        second_byte="unsigned char",
        f_start_pos=Py_ssize_t,
        f_end_pos=Py_ssize_t,
        has_mask=bint,
        fin=bint,
        had_fragments=Py_ssize_t,
        payload_bytearray=bytearray,
    )
    cpdef void _feed_data(self, bytes data) except *
