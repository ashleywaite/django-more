from functools import partial
from functools import partialmethod
from django.db import models
from django.db.models import Case
from django.db.models import Max
from django.db.models import Q
from django.db.models import Subquery
from django.db.models import When
from django.db.models.functions import Coalesce
from django.db.models.fields.related import resolve_relation, make_model_tuple

from django_types.utils import dependency_tuple

from ..expressions import BypassExpression
from .mixins import UniqueForFieldsMixin


class OrderByField(UniqueForFieldsMixin, models.Field):
    """ Integer that determine display or sort order of records """
    # Function name templates
    func_local_next = 'get_next_in_order'
    func_local_previous = 'get_previous_in_order'
    func_local_get_set = 'get_%(name)s_set'
    func_local_set_set = 'set_%(name)s_set'
    func_remote_get_set = 'get_%(model)s_set'
    func_remote_set_set = 'set_%(model)s_set'

    # Will use unique_for_fields if specified, otherwise unique by default
    def __init__(self, *args, **kwargs):
        if 'default' in kwargs:
            raise ValueError('OrderByField may not have a default value')
        # Default None suppresses migration requests to set a default
        # TODO Add automatically filling to migrations
        super().__init__(*args, default=None, **kwargs)

    def get_dependencies(self):
        return [
            dependency_tuple(
                app_label=self.model._meta.app_label,
                object_name=self.model._meta.object_name,
                field=field.name,
                created=True)
            for field_name in self.unique_for_fields
            for field in (self.model._meta.get_field(field_name), )]

    def contribute_to_class(self, cls, *args, **kwargs):
        super().contribute_to_class(cls, *args, **kwargs)

        # Add order related methods to model
        # Applying partialmethod() to already bound methods will retain self and add the model_instance bound to
        subs = {'name': self.name, 'model': self.model.__name__.lower()}
        setattr(cls, self.func_local_next % subs, partialmethod(self.get_next_or_previous_in_order, is_next=True))
        setattr(cls, self.func_local_previous % subs, partialmethod(self.get_next_or_previous_in_order, is_next=False))
        setattr(cls, self.func_local_get_set % subs, partialmethod(self.get_group_order))
        setattr(cls, self.func_local_set_set % subs, partialmethod(self.set_group_order))
        if self.unique_for_fields:
            # Declare that this field has dependencies
            self.has_dependencies = True
            # Queue rest of work for when model is fully loaded
            cls._meta.apps.lazy_model_operation(
                self._lazy_contribute_to_class,
                (cls._meta.app_label, cls._meta.model_name))

    def _lazy_contribute_to_class(self, model):
        # Sanity check
        assert(self.model == model)
        # Get foreign keys in the grouping
        field_fks = {
            field.name: field
            for field_name in self.unique_for_fields
            for field in (model._meta.get_field(field_name), )
            if not field.auto_created and field.many_to_one}

        # Extract all associated generic relations
        generic_fks = {
            field.name: field
            for field in model._meta.local_fields
            if (field.many_to_one and not field.remote_field)             # find generic fks
            and (field.name in field_fks or field.fk_field in field_fks)  # associated with this grouping
            and field_fks.pop(field.name, True)                           # and discard their fields
            and field_fks.pop(field.fk_field, True)}                      # from the field_fks list

        # Queue creation of remote order accessors
        for field in field_fks.values():
            model._meta.apps.lazy_model_operation(
                partial(self.contribute_to_related_class, field=field),
                make_model_tuple(resolve_relation(model, field.remote_field.model)))

        # TODO Find GenericRelations and add accessors

    def contribute_to_related_class(self, cls, field):
        subs = {'name': self.name, 'model': self.model.__name__.lower(), 'remote_name': field.name}
        setattr(cls, self.func_remote_get_set % subs, partialmethod(self.get_group_order, field=field))
        setattr(cls, self.func_remote_set_set % subs, partialmethod(self.set_group_order, field=field))

    def get_internal_type(self):
        return "PositiveIntegerField"

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Remove default from field definition
        kwargs.pop('default', None)
        return name, path, args, kwargs

    def get_next_or_previous_in_order(self, model_instance, is_next=True):
        if not model_instance.pk:
            raise ValueError("get_next/get_previous cannot be used on unsaved objects.")
        group_qs = self.get_group(model_instance).order_by(self.attname)
        # Filter out everything on the wrong side of this record
        filter_clause = '{field}__{direction}'.format(
            field=self.attname,
            direction='gt' if is_next else 'lt')
        filtered = group_qs.filter(**{filter_clause: getattr(model_instance, self.attname)})
        # Return the right end based on direction
        if is_next:
            return filtered.first()
        return filtered.last()

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
