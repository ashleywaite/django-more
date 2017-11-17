from functools import partialmethod
from django.db import models
from django.db.models import Case
from django.db.models import Max
from django.db.models import Q
from django.db.models import Subquery
from django.db.models import When
from django.db.models.functions import Coalesce

from ..expressions import BypassExpression
from .mixins import UniqueForFieldsMixin


class OrderByField(UniqueForFieldsMixin, models.IntegerField):
    """ Integer that determine display or sort order of records """
    # Function name templates
    func_local_get_set = 'get_%(name)s_set'
    func_local_set_set = 'set_%(name)s_set'

    # Will use unique_for_fields if specified, otherwise unique by default
    def __init__(self, *args, **kwargs):
        if 'default' in kwargs:
            raise ValueError('OrderByField may not have a default value')
        # Default None suppresses migration requests to set a default
        # TODO Add automatically filling to migrations
        super().__init__(*args, default=None, **kwargs)

    def contribute_to_class(self, cls, *args, **kwargs):
        super().contribute_to_class(cls, *args, **kwargs)
        # Add order related methods to model
        # Applying partialmethod() to already bound methods will retain self and add the model_instance bound to
        subs = {'name': self.name, 'model': self.model.__name__.lower()}
        setattr(cls, self.func_local_get_set % subs, partialmethod(self.get_group_order))
        setattr(cls, self.func_local_set_set % subs, partialmethod(self.set_group_order))
    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Remove default from field definition
        kwargs.pop('default', None)
        return name, path, args, kwargs

    def pre_save(self, model_instance, add):
        # Default to the next number larger than existing records, or start from 0
        if add and not getattr(model_instance, self.attname):
            return self.get_next_expression(model_instance)
        else:
            return super().pre_save(model_instance, add)

    def get_next_expression(self, model_instance):
        """ Generate an expression that will evaluate to the next valid ordering value """
        # This will be the next number larger than existing records in the ordering set
        # If no records in the ordering set, start from 0
        # Evade any custom model managers
        qs = models.QuerySet(self.model).filter(**self.get_filter_kwargs_for_object(model_instance))
        qs = qs.annotate(_next=Max(self.attname) + 1).values('_next').order_by()
        # Hackishly clip group_by clause to guarantee single result
        qs.query.group_by = []
        return BypassExpression(Coalesce(Subquery(qs), 0, output_field=models.IntegerField()))

    def get_group_order(self, model_instance, *, field=None, limit_to=None):
        """ Get the ordered group associated with an object
            * model_instance :: (bound) Source instance of the call
            * field :: Local fk that connects to source model if it's remote
            * limit_to :: An optional self.model instance to limit to one group
              when doing a remote call into composite fk groupings
        """
        filters = Q()
        if field:
            # Apply filter from remote field calls
            filters &= Q(**field.forward_related_filter(model_instance))
            if limit_to:
                # Apply local additive filter for remote field calls
                filters &= Q(**self.get_filter_kwargs_for_object(limit_to))
        else:
            # Apply filter for local field calls
            filters &= Q(**self.get_filter_kwargs_for_object(model_instance))
        return self.model.objects.filter(filters).order_by(*self.group_attnames, self.attname).values_list('pk', flat=True)

    def set_group_order(self, model_instance, id_list, *, field=None, reset_values=False, using=None):
        """ Set the ordering for a group
            * model_instance :: (bound) Source instance of the call
            * id_list :: List of primary keys (or a queryset) that will be moved
              to the end of their ordering set in order
              Has the effect of reordering all listed to match order specified
            * field :: Local fk that connects to source model if it's remote
            * reset_values :: Boolean to indicate whether to freshly renumber
              entire group from 0
              Must be updating entire group to reset_values
        """
        # Case expression to number instances in correct order
        enum_case = Case(*[When(pk=pk, then=i) for i, pk in enumerate(id_list)])
        # Bulk update with next value + enumerated value
        group_qs = self.get_group(model_instance)
        update_qs = group_qs.filter(pk__in=id_list)
        update_count = update_qs.update(**{self.attname: self.get_next_expression(model_instance) + enum_case})
        # Can only safely reset up whole group was updated
        if reset_values and update_count == group_qs.count():
            # Bulk update with just enumerated value
            update_qs.update(**{self.attname: enum_case})

        # TODO Even better with enumerated CTE

        # NOTE Possible fallback for some dbs? Update sequentially
        # for pk in id_list:
        #    qs.filter(pk=pk).update(**{self.attname: value})
