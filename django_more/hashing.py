
from base64 import b64encode, b16encode, b64decode, b16decode
from math import ceil

__all__ = [
    "b64max",
    "b64len",
    "b64from16",
    "b64from256",
    "b16len",
    "b16max",
    "b16from64",
    "b16from256",
    "HashString",
]


# Base 64 helpers for working in strings
# b64 encodes 6 bits per character, in 3 byte raw increments, four bytes b64
def b64max(char_length):
    """ Maximum number of raw bits that can be stored in a b64 of length x """
    # Four byte increments only, discard extra length
    return (char_length // 4) * (3 * 8)


def b64len(bit_length):
    """ Minimum b64 length required to hold x raw bits """
    # Three raw bytes {bl / (8*3)} is four b64 bytes
    return ceil(int(bit_length) / (8 * 3)) * 4


def b64from16(val):
    """ ASCII encoded base 64 string from a base 16 digest """
    return b64from256(b16decode(val, casefold=True))


def b64from256(val):
    """ ASCII encoded base 64 string from a raw (base 256) digest """
    return str(b64encode(bytes(val)), encoding="ascii")


# Base 16 helpers for working in strings
# b16 encodes 4 bits per character
def b16len(bit_length):
    """ Minimum b16/hex length required to hold x raw bits """
    return ceil(int(bit_length) / 4)


def b16max(char_length):
    """ Maximum number of raw bits that can be stored in a b16 of length x """
    return int(char_length) * 4


def b16from64(val):
    """ ASCII encoded base 16 string from a base 64 digest """
    return b16from256(b64decode(val))


def b16from256(val):
    """ ASCII encoded base 16 string from a raw (base 256) digest """
    return str(b16encode(bytes(val)), encoding="ascii")


class HashString(str):

    b64to = {
        "b16": b16from64,
        "b64": str.__str__,
        "b256": b64decode,
    }
    b16to = {
        "b64": b64from16,
        "b16": str.__str__,
        "b256": b16decode,
    }

    def __new__(cls, value):
        return super().__new__(cls, value)

    def __getattr__(self, attr):
        try:
            setattr(self, attr, self.b_to[attr](self))
            return getattr(self, attr)
        except KeyError:
            raise AttributeError

    @classmethod
    def from_b64(cls, value):
        """ Create from a base 64 value """
        self = cls(value)
        self.b_to = self.b64to
        return self

    @classmethod
    def from_b16(cls, value):
        """ Create from a base 16 value """
        self = cls(value)
        self.b_to = self.b16to
        return self

    @classmethod
    def from_b256(cls, value):
        """ Create from a raw (base 256) value """
        self = cls.from_b64(b64from256(value))
        self.b256 = value
        return self

    def __eq__(self, value):
        if isinstance(value, str):
            if str.__eq__(self, value):
                return True
            if str.__eq__(self.b64, value):
                # Check for encoding sensitive matches
                return True
            if str.__eq__(str(self), str.lower(value)):
                # Check for lower case matches of base 16
                return True
        elif isinstance(value, bytes) and bytes.__eq__(self.b256, value):
            return True
        return False

    def __bytes__(self):
        # Bytes will give the base256 / raw bytes
        return self.b256

    def __str__(self):
        # Stringy informal representations of hashes are base16 lowercase
        return str.lower(self.b16)

    def __repr__(self):
        # Formal accurate representations of hases are base64
        return self.b64

    def __hash__(self):
        # Hashing always uses base64 for consistency
        return hash(self.b64)
