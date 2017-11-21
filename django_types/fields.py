
from contextlib import suppress

from django.db import models
from django.utils.module_loading import import_string
from django.utils.datastructures import DictWrapper
from django.apps import apps

__all__ = ['CustomTypeField']


class CustomTypeField(models.Field):
    type_def_subclass = object
    type_name = None
    _type_def = None
    type_app_label = None

    data_types = {
        'vendor': 'db_type_format'
    }

    def __init__(self, *args, type_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        if type_name:
            self.type_name = type_name

    @property
    def type_def(self):
        return self._type_def

    # Perform general initialisation required for custom types to have access to meta information
    @type_def.setter
    def type_def(self, type_def):
        if isinstance(type_def, str):
            type_def = import_string(type_def)

        if not issubclass(type_def, self.type_def_subclass):
            raise TypeError('type_def must be a subclass of {}'.format(self.type_def_subclass))

        # Import meta options from type_def
        with suppress(AttributeError):
            self.type_name = type_def.Meta.db_type
        with suppress(AttributeError):
            self.type_app_label = type_def.Meta.app_label

        if not self.type_app_label:
            # Determine app_label of enum being used
            app_config = apps.get_containing_app_config(type_def.__module__)
            if app_config is None:
                raise RuntimeError(
                    "type_def class doesn't declare an explicit app_label, and isn't"
                    " in an application in INSTALLED_APPS")
            self.type_app_label = app_config.label

        # Generate type_name if not already set
        if not self.type_name:
            self.type_name = '{app_label}_{type_subclass}_{type_name}'.format(
                app_label=self.type_app_label,
                type_subclass=self.type_def_subclass.__name__.lower(),
                type_name=type_def.__qualname__.lower())

        self._type_def = type_def

    def contribute_to_class(self, cls, *args, **kwargs):
        super().contribute_to_class(cls, *args, **kwargs)
        # Add hook to access stateful information in StateApps in migrations
        if self.type_name and not self.type_def:
            with suppress(AttributeError, KeyError):
                apps = cls._meta.apps
                type_def = apps.db_types[self.type_name]
                self.type_def = type_def

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.type_name:
            kwargs['type_name'] = self.type_name
        return name, path, args, kwargs

    def clone(self):
        # Override deconstruct behaviour to include live type if available
        obj = super().clone()
        if self.type_def:
            obj.type_def = self.type_def
        return obj

    # Provided for Django 1.11 compatibility
    def db_type_parameters(self, connection):
        return DictWrapper(self.__dict__, connection.ops.quote_name, 'qn_')

    # Subclasses should take this value and add parametised values with str overload DBType
    def db_type(self, connection):
        # Attempt local lookup
        type_format = self.data_types.get(connection.vendor) or self.data_types.get('unknown')
        if isinstance(type_format, type):
            type_format = connection.data_types[type_format.__name__]
        if not type_format:
            type_format = super().db_type(connection)

        # Do generalised parameter substitution
        type_string = type_format % self.db_type_parameters(connection)

        return type_string
