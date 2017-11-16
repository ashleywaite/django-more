from django.db.models.options import normalize_together
from django.utils.functional import cached_property


# Used by OrderByField to allow for unique_together constraints to be field declared
class UniqueForFieldsMixin:
    """ Mixin first to a Field to add a unique_for_fields field option """
    unique_for_fields = None

    def __init__(self, unique_for_fields=None, *args, **kwargs):
        if unique_for_fields:
            self.unique_for_fields = tuple(unique_for_fields)
            # If unique_for_fields then any unique option is irrelevant
            kwargs.pop('unique', None)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.unique_for_fields:
            kwargs['unique_for_fields'] = self.unique_for_fields
        return name, path, args, kwargs

    def contribute_to_class(self, cls, *args, **kwargs):
        super().contribute_to_class(cls, *args, **kwargs)

        # Add any necessary unique_together index to the model
        if self.unique_for_fields:
            # Alter only original_attr to fake being a declared unique_together
            # Cannot modify cls._meta.unique_together as it breaks state consistency for migrations
            ut = set((self.unique_together, )).union(normalize_together(cls._meta.original_attrs.get('unique_together')))
            cls._meta.original_attrs['unique_together'] = ut

    @cached_property
    def unique_together(self):
        return self.unique_for_fields + (self.attname, )

    @cached_property
    def unique_for_attnames(self):
        return [self.model._meta.get_field(field_name).get_attname() for field_name in self.unique_for_fields]
