from django.db import models
from django.db.models import Max
from django.db.models import Subquery
from django.db.models.functions import Coalesce

from ..expressions import BypassExpression
from ..mixins import UniqueForFieldsMixin


class OrderByField(UniqueForFieldsMixin, models.IntegerField):
    """ Integer that determine display or sort order of records """
    # Must always have some unique constraint
    # Will use unique_for_fields if specified, otherwise unique by default

    def __init__(self, *args, **kwargs):
        if 'default' in kwargs:
            raise ValueError('OrderByField may not have a default value')
        if 'unique' in kwargs:
            raise ValueError('OrderByField may not be explicitly declared unique')
        super().__init__(*args, unique=True, default=None, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Remove unique from field definition
        kwargs.pop('unique', None)
        kwargs.pop('default', None)
        return name, path, args, kwargs

    def pre_save(self, model_instance, add):
        # Default to the next number larger than existing records, or 1
        if add and not getattr(model_instance, self.attname):
            # Evade any custom model managers
            qs = models.QuerySet(self.model)
            # Apply additional uniqueness filters if applicable
            unique_for_values = {
                attname: getattr(model_instance, attname)
                for attname in self.unique_for_attnames}
            if unique_for_values:
                qs = qs.filter(**unique_for_values)
            qs = qs.annotate(_next=Max(self.attname) + 1).values('_next').order_by()
            # Hackishly clip group_by clause to guarantee single result
            qs.query.group_by = []
            return BypassExpression(Coalesce(Subquery(qs), 1, output_field=models.IntegerField()))
