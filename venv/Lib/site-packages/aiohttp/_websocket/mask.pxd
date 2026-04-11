"""Cython declarations for websocket masking."""

cpdef void _websocket_mask_cython(bytes mask, bytearray data)
