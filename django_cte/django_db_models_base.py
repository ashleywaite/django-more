
from django.db.models.query import LiteralQuerySet


class Model:

    @classmethod
    def as_literal(cls, values=None, using=None, enum_field=None):
        return LiteralQuerySet(model=cls, values=values, enum_field=None, using=using)
