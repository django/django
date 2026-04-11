def murmur3_32(data, seed=0):
    """MurmurHash3 was written by Austin Appleby, and is placed in the
    public domain. The author hereby disclaims copyright to this source
    code."""

    c1 = 0xCC9E2D51
    c2 = 0x1B873593

    length = len(data)
    h1 = seed
    roundedEnd = length & 0xFFFFFFFC  # round down to 4 byte block
    for i in range(0, roundedEnd, 4):
        # little endian load order
        k1 = (
            (ord(data[i]) & 0xFF)
            | ((ord(data[i + 1]) & 0xFF) << 8)
            | ((ord(data[i + 2]) & 0xFF) << 16)
            | (ord(data[i + 3]) << 24)
        )
        k1 *= c1
        k1 = (k1 << 15) | ((k1 & 0xFFFFFFFF) >> 17)  # ROTL32(k1,15)
        k1 *= c2

        h1 ^= k1
        h1 = (h1 << 13) | ((h1 & 0xFFFFFFFF) >> 19)  # ROTL32(h1,13)
        h1 = h1 * 5 + 0xE6546B64

    # tail
    k1 = 0

    val = length & 0x03
    if val == 3:
        k1 = (ord(data[roundedEnd + 2]) & 0xFF) << 16
    # fallthrough
    if val in [2, 3]:
        k1 |= (ord(data[roundedEnd + 1]) & 0xFF) << 8
    # fallthrough
    if val in [1, 2, 3]:
        k1 |= ord(data[roundedEnd]) & 0xFF
        k1 *= c1
        k1 = (k1 << 15) | ((k1 & 0xFFFFFFFF) >> 17)  # ROTL32(k1,15)
        k1 *= c2
        h1 ^= k1

    # finalization
    h1 ^= length

    # fmix(h1)
    h1 ^= (h1 & 0xFFFFFFFF) >> 16
    h1 *= 0x85EBCA6B
    h1 ^= (h1 & 0xFFFFFFFF) >> 13
    h1 *= 0xC2B2AE35
    h1 ^= (h1 & 0xFFFFFFFF) >> 16

    return h1 & 0xFFFFFFFF
