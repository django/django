"""
Django's standard token library and utilities. 
"""

import hashlib
import string
import random

try:
    random = random.SystemRandom()
except NotImplementedError:
    random = random.random()

"""
Character sets for the various tokens and hashes.
"""
DIGITS = string.digits
UPPERCASE = string.uppercase
LOWERCASE = string.lowercase
HEX = string.digits + 'abcdef'
ALPHANUMERIC = string.digits + string.uppercase + string.lowercase
LOWER_ALPHANUMERIC = string.digits + string.lowercase
# remove for human consumption - we don't want confusion between letter-O and zero
# effectively: for i in 'ilIoO01': x.remove(i)
READABLE_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijklmnpqrstuvwxyz'

DEFAULT_TOKEN_LENGTH = 32

class RandomToken():
    """
    Object that creates randomized token.
    """
    def digits(self, length=DEFAULT_TOKEN_LENGTH):
        """
        Creates a randomized token consisting of the DIGIT character set.
        """
        return self._build_token(DIGITS, length)
    
    def alphanumeric(self, length=DEFAULT_TOKEN_LENGTH):
        """
        Creates a randomized token consisting of the general ALPHANUMERIC character sets.
        """
        return self._build_token(ALPHANUMERIC, length)
    
    def lower_alphanumeric(self, length=DEFAULT_TOKEN_LENGTH):
        """
        Creates a randomized token consisting of the LOWER_ALPHANUMERIC character sets.
        """
        return self._build_token(LOWER_ALPHANUMERIC, length)
    
    def hex(self, length=DEFAULT_TOKEN_LENGTH):
        """
        Creates a randomized token consisting of the HEX character sets.
        """
        return self._build_token(HEX, length)
    
    def readable_alphanumeric(self, length=DEFAULT_TOKEN_LENGTH):
        """
        Creates a randomized token consisting of the READABLE_ALPHABET character set.
        """
        return self._build_token(READABLE_ALPHABET, length)
    
    def _build_token(self, character_set, length):
        """
        Builds a random token of the specified length using the characters available in the specified character set.
        """
        return ''.join([random.choice(character_set) for i in xrange(length)])


class HashToken():
    """
    Return a token useful for a hash (that is, a token whose generation is repeatable)
    """
    def __init__(self, value=''):
        self._hash = hashlib.sha256(value)

    def digits(self):
        return _build_token(DIGITS)
        
    def hex(self):
        """ Outputs a base 16 string. """
        return self._hash.hexdigest()
    
    def alphanumenric(self, casesensitive=True):
        return _build_token(ALPHANUMERIC)
    
    def lower_alphanumeric(self):
        """
        Creates a randomized token consisting of the LOWER_ALPHANUMERIC character sets.
        """
        return self._build_token(LOWER_ALPHANUMERIC)
    
    def readable_alphanumeric(self):
        """
        Creates a randomized token consisting of the READABLE_ALPHABET character set.
        """
        return self._build_token(READABLE_ALPHABET)
    
    def _build_token(self, alphabet):
        """ Outputs our hash to an alphabet specified string. """
        hextoken = self._hash.hexdigest()
        converter = BaseConverter(alphabet)
        return converter.encode(int(hextoken, 16))

    def update(self, value):
        self._hash = self._hash.update(value)
