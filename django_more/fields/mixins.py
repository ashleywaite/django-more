from django.db.models.options import normalize_together
from django.utils.functional import cached_property


# Used by OrderByField to allow for unique_together and db_constraint to be field declared
class UniqueForFieldsMixin:
    """ Mixin first to a Field to add a unique_for_fields field option """
    unique_for_fields = None
    db_constraint = None

    def __init__(self, unique_for_fields=None, db_constraint=True, *args, **kwargs):
        if 'unique' in kwargs:
            raise ValueError('{cls} may not be explicitly declared unique'.format(cls=self.__class__))
        if unique_for_fields:
            self.unique_for_fields = tuple(unique_for_fields)
        else:
            kwargs['unique'] = True
        # Use different internal name to dodge schema_editor checks that make fk constraints
        self.unique_db_constraint = db_constraint
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.unique_for_fields:
            kwargs['unique_for_fields'] = self.unique_for_fields
        kwargs['db_constraint'] = self.unique_db_constraint
        # Remove unique from field definition
        kwargs.pop('unique', None)
        return name, path, args, kwargs

    def contribute_to_class(self, cls, *args, **kwargs):
        super().contribute_to_class(cls, *args, **kwargs)

        # Add any necessary unique_together index to the model
        if self.unique_for_fields and self.unique_db_constraint:
            # Alter only original_attr to fake being a declared unique_together
            # Cannot modify cls._meta.unique_together as it breaks state consistency for migrations
            ut = set((self.unique_together, )).union(normalize_together(cls._meta.original_attrs.get('unique_together')))
            cls._meta.original_attrs['unique_together'] = ut

    def get_filter_kwargs_for_object(self, model_instance):
        """
        Return a dict that when passed as kwargs to self.model.filter(), would
        yield all instances within this grouping.
        """
        return {
            attname: getattr(model_instance, attname)
            for attname in self.group_attnames}

    def get_group(self, model_instance):
        return self.model.objects.filter(**self.get_filter_kwargs_for_object(model_instance))

    @cached_property
    def unique_together(self):
        return self.unique_for_fields + (self.name, )

    @cached_property
    def group_attnames(self):
        return [self.model._meta.get_field(field_name).get_attname() for field_name in self.unique_for_fields]
