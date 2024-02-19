# https://github.com/python-trio/trio/issues/2873
import trio

s, r = trio.open_memory_channel[int](0)
