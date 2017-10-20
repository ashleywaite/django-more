
from enum import Enum
from django.db import models
from django_enum import EnumField, enum_meta


class TestEnum(Enum):
    VAL1 = 'The first value'
    VAL2 = 'The second value'
    VAL3 = 'Third value is the best'


class WrongEnum(Enum):
    VAL1 = 'The first wrong value'
    VAL2 = 'Another one wrong'
    VAL3 = 'Third value is the best'


class MetaEnum(Enum):
    VAL1 = 'First meta value'
    VAL2 = 'So meta'
    VAL3 = 'Third value is the best'
    @enum_meta
    class Meta:
        db_type = 'test_enum_meta'


class FirstModel(models.Model):
    test_enum = EnumField(TestEnum)
    meta_enum = EnumField(MetaEnum)
