from django.db import models
from django.db.models import BLANK_CHOICE_DASH
from django.core.exceptions import ValidationError
from contextlib import suppress


class EnumField(models.CharField):
    description = 'Enumeration field using python PEP435 and database implementations'
    case_sensitive = None
    enum_type = None

    def __init__(self, enum, case_sensitive=None, **kwargs):
        # TODO Add case insensitive enum
        if case_sensitive is not None:
            self.case_sensitive = case_sensitive

        if isinstance(enum, str):
            # Used for migrations only. Cannot specify enum by lazy class name
            self.enum_type = enum_type
        else:
            self.coerce_enum_class(enum)
            self.enum = enum
            self.enum.Meta.related_fields.append(self)
        super().__init__(**kwargs)

    @classmethod
    def coerce_enum_class(cls, enum):
        """ Add Django attributes to a regular python enum if not present """
        if not hasattr(enum, 'Meta'):
            enum.Meta = type('Meta', object, {})

        if not hasattr(enum.Meta, 'db_type'):
            # Look for an application configuration to attach the enum to
            app_config = apps.get_containing_app_config(enum.__module__)
            if app_config is None:
                raise RuntimeError(
                    "Enum class doesn't declare an explicit app_label, and isn't"
                    " in an application in INSTALLED_APPS")
            enum.Meta.app_label = app_config.label
            enum.Meta.name = enum.__qualname__.lower()
            enum.Meta.db_type = '{al}_enum_{en}'.format(
                al=enum.Meta.app_label,
                en=enum.Meta.name)

        if not hasattr(enum.Meta, 'related_fields'):
            enum.Meta.related_fields = []

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['enum'] = self.enum_type or self.enum.Meta.db_type
        if self.case_sensitive is not None:
            kwargs['case_sensitive'] = self.case_sensitive
        return name, path, kwargs

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
            paras.update(enum_type=self.enum_type or self.enum.Meta.db_type)
        else:
            paras.update(choices=','.join(
                "'{}'".format(c) for c in self.get_choices()))
        return paras
