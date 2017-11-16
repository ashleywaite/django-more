""" Declare custom Django fields """
from django.core.exceptions import ValidationError
from django.db import models

from ..hashing import b16len, b64len, b64max, HashString


__all__ = ['HashField']


class HashField(models.CharField):
    description = "Hash field stored as base64, with string-like HashString as python representation"

    def __init__(self, bit_length=None, max_length=None, *args, **kwargs):
        if not bit_length and max_length:
            # If no bit_length specified, use maximum that will fit in max_length
            bit_length = b64max(max_length)
        if bit_length:
            self.bit_length = bit_length
            self.b64_length = b64len(bit_length)
            self.b16_length = b16len(bit_length)
            if not max_length or max_length < self.b64_length:
                max_length = self.b64_length
        else:
            raise ValueError("HashField requires a bit_length or max_length")
        kwargs["max_length"] = max_length
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["bit_length"] = self.bit_length
        if kwargs["max_length"] == b64len(self.bit_length):
            del kwargs["max_length"]
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return None
        return HashString.from_b64(value)

    def to_python(self, value):
        if value is None or isinstance(value, HashString):
            return value

        val = self.coerce(value)
        if val:
            return val
        raise ValidationError("Cannot determine hash format")

    def get_prep_value(self, value):
        if not value:
            return value
        if not isinstance(value, HashString):
            value = self.coerce(value)
        return value.b64

    def coerce(self, value):
        """ Attempt to detect likely encoding and create """
        if isinstance(value, bytes) and len(value) == self.bit_length:
            return HashString.from_b256(value)
        elif len(value) == self.b16_length:
            return HashString.from_b16(value)
        elif self.b64_length - len(value) <= 4:
            return HashString.from_b64(value)
