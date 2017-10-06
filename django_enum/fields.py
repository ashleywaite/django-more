from django.db import models
from django.db.models import BLANK_CHOICE_DASH
from django.core.exceptions import ValidationError
from django.apps import apps
from django.utils.module_loading import import_string
from contextlib import suppress

__all__ = ['EnumField']


class DBType(str):
    """ Create a db_type string that can represent paramatised values """
    params = []
    db_type = None

    def __new__(cls, value, params=None, *args, **kwargs):
        if not params:
            return super().__new__(cls, value)
        self = super().__new__(cls, cls.render(value, params))
        self.db_type = value
        self.params = params
        return self

    @property
    def paramatized(self):
        return self.db_type or self, params

    @staticmethod
    def render(db_type, params):
        return db_type % tuple(params)


class EnumField(models.Field):
    description = 'Enumeration field using python PEP435 and database implementations'
    case_sensitive = None
    enum_type = None
    enum = None
    enum_app = None

    def __init__(self, enum=None, enum_type=None, case_sensitive=None, **kwargs):
        if case_sensitive is not None:
            self.case_sensitive = case_sensitive

        if isinstance(enum, str):
            with suppress(ImportError):
                self.enum = import_string(enum)
        else:
            self.enum = enum

        if self.enum:
            # Determine app_label of enum being used
            app_config = apps.get_containing_app_config(self.enum.__module__)
            if app_config is None:
                raise RuntimeError(
                    "Enum class doesn't declare an explicit app_label, and isn't"
                    " in an application in INSTALLED_APPS")
            self.enum_app = app_config.label

        # Respect the db_type declared on the enum, else generate
        if enum_type:
            self.enum_type = enum_type
        else:
            if 'Meta' in self.enum and 'db_type' in self.enum.Meta:
                self.enum_type = self.enum.Meta.db_type
            else:
                self.enum_type = '{al}_enum_{en}'.format(
                    al=self.enum_app,
                    en=self.enum.__qualname__.lower())

        # Trickery that allows Django on_delete functionality to work
        self.remote_field = self

        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['enum_type'] = self.enum_type
        if self.case_sensitive is not None:
            kwargs['case_sensitive'] = self.case_sensitive
        return name, path, args, kwargs

    def clone(self):
        # Override deconstruct behaviour to include live enum
        obj = super().clone()
        if self.enum:
            obj.enum = self.enum
        return obj

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
        # Enum match failed, if not case_sensitive, try insensitive scan
        if self.case_sensitive is False:
            for em in self.enum:
                if str(value).lower() == em.value.lower():
                    return em
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
        if connection.features.has_enum:
            paras['enum_type'] = self.enum_type
            paras['values'] = ', '.join('%s' * len(self.get_choices()))
        return paras

    def db_type(self, connection):
        type_string = super().db_type(connection)
        choices = None
        if connection.features.has_enum and not connection.features.requires_enum_declaration:
            choices = self.get_choices()

        return DBType(
            type_string,
            choices)
