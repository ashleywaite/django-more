from django.db import models
from django.db.models import BLANK_CHOICE_DASH
from django.core.exceptions import ValidationError
from django.apps import apps
from django.utils.module_loading import import_string
from contextlib import suppress

__all__ = ['EnumField']

class EnumField(models.Field):
    description = 'Enumeration field using python PEP435 and database implementations'
    case_sensitive = None
    enum_type = None

    def __init__(self, enum, enum_type=None, case_sensitive=None, **kwargs):
        # TODO Add case insensitive enum
        if case_sensitive is not None:
            self.case_sensitive = case_sensitive

        if isinstance(enum, str):
            # Used for migrations only. Cannot specify enum by lazy class name
            self.enum = import_string(enum)
        else:
            self.enum = enum

        app_config = apps.get_containing_app_config(self.enum.__module__)
        if app_config is None:
            raise RuntimeError(
                "Enum class doesn't declare an explicit app_label, and isn't"
                " in an application in INSTALLED_APPS")
        self.enum_app = app_config.label

        if enum_type:
            self.enum_type = enum_type
        else:
            if 'Meta' in self.enum and 'db_type' in self.enum.Meta:
                self.enum_type = self.enum.Meta.db_type
            else:
                self.enum_type = '{al}_enum_{en}'.format(
                    al=self.enum_app,
                    en=self.enum.__qualname__.lower())
        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['enum'] = '{}.{}'.format(self.enum.__module__, self.enum.__name__)
        kwargs['enum_type'] = self.enum_type
        if self.case_sensitive is not None:
            kwargs['case_sensitive'] = self.case_sensitive
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return None
        with suppress(KeyError):
            return self.enum[value]
        raise ValueError('Invalid enumeration value returned from database')

    def to_python(self, value):
        if value is None or isinstance(value, self.enum):
            return value
        with suppress(ValueError):
            # Key miss suppressed with .get()
            return self.enum.__members__.get(value) or self.enum(value)
        raise ValidationError('Invalid enumeration value')

    def get_prep_value(self, value):
        if not value:
            return value
        if not isinstance(value, self.enum):
            value = self.to_python(value)
        return value.value

    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH, limit_choices_to=None):
        return [e.value for e in self.enum]

    # db_type method not needed if parameters set
    def db_type_parameters(self, connection):
        paras = super().db_type_parameters(connection)
        # If connection type with enum type declarations
        if connection.features.requires_enum_declaration:
            paras.update(enum_type=self.enum_type)
        else:
            paras.update(choices=','.join(
                "'{}'".format(c) for c in self.get_choices()))
        return paras
