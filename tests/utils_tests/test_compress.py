# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import warnings

from django.test import SimpleTestCase
from django.utils.text import compress_string, compress_sequence
from gzip import GzipFile
from io import BytesIO

class HashOverriddenString(str):
    """
    Gzip Breach resistance seeds Random from the string hash.

    This class provides a version of string with an overrideable hash
    to simulate the case of two files that compress to the same size
    but have a different.
    """

    def __init__(self, v):
        str.__init__(self, v)

    def __call__(self, v):
        ho = HashOverriddenString(v)
        ho.hash = v.hash
        return ho

    def __hash__(self):
        return self.hash


class GzipBreachResistanceTests:
    """
    A collection of tests
    """
    DATA = open(__file__).read()
    def test_compression_works(self):
        "Confirm compression/decompression results in an unchanged file."
        self.assertEquals(GzipFile(fileobj = BytesIO(self.compress(self.DATA))).read(),
                          self.DATA)

    def test_compression_sizes_do_not_differ(self):
        "Confirm two identical strings have the same compression parameters to prevent an averaging attack."
        self.assertTrue(len(set(len(self.compress(self.DATA)) for x in range(100))) == 1 )

    def test_zero_length_regress(self):
        "Compressing a zero length string should not result in a DivsionByZero error."
        self.compress('') # Shouldn't raise a DivisionByZero error

    def test_same_strings_different_hash_are_compressed_randomly(self):
        "Confirm two strings with different hashs are compressed differently most of the time."
        strings = map(HashOverriddenString, [self.DATA,] * 20)
        for v, string in enumerate(strings):
            string.hash = v

        strings = set(map(len, map(self.compress, strings)))
        self.assertTrue(len(strings) > 1,
                        msg="Make sure we have more than one compressed size for our compressed string")


class TestStringCompression(GzipBreachResistanceTests, SimpleTestCase):
    """Apply all of GzipBreachResistanceTests against a string."""

    def compress(self, s):
        return compress_string(s)


class TestSequenceCompression(GzipBreachResistanceTests, SimpleTestCase):
    """Apply all of GzipBreachResistanceTests against a streamed sequence."""

    def compress(self, s_orig):
        s = s_orig
        chunk, s = s[:1024], s[1024:]
        if isinstance(s_orig, HashOverriddenString):
            chunk = HashOverriddenString(chunk)
            chunk.hash = s.hash
        chunks = []
        while chunk:
            chunks.append(chunk)
            chunk, s = s[:1024], s[1024:]
            if isinstance(s_orig, HashOverriddenString):
                chunk = HashOverriddenString(chunk)
                chunk.hash = s.hash
        print map(type, chunks)
        return bytes(''.join(compress_sequence(chunks)))

