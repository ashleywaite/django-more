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
    _enum = None
    enum_app = None
    manual_choices = False

    def __init__(self, enum=None, enum_type=None, case_sensitive=None, **kwargs):
        super().__init__(**kwargs)
        if kwargs.get('choices', False):
            self.manual_choices = True
        if enum:
            self.enum = enum
        if enum_type:
            self.enum_type = enum_type
        if case_sensitive is not None:
            self.case_sensitive = case_sensitive
        # Trickery that allows Django on_delete functionality to work
        self.remote_field = self

    @property
    def enum(self):
        return self._enum

    @enum.setter
    def enum(self, enum):
        if isinstance(enum, str):
            enum = import_string(enum)

        # Import meta options from enum
        if 'Meta' in enum:
            if 'db_type' in enum.Meta:
                self.enum_type = enum.Meta.db_type
            if 'app_label' in enum.Meta:
                self.enum_app = enum.Meta.app_label

        if not self.enum_app:
            # Determine app_label of enum being used
            app_config = apps.get_containing_app_config(enum.__module__)
            if app_config is None:
                raise RuntimeError(
                    "Enum class doesn't declare an explicit app_label, and isn't"
                    " in an application in INSTALLED_APPS")
            self.enum_app = app_config.label

        # Generated enum_type
        if not self.enum_type:
            self.enum_type = '{al}_enum_{en}'.format(
                al=self.enum_app,
                en=enum.__qualname__.lower())

        # Allow enum members as choices
        if self.manual_choices:
            self.choices = [
                (choice.name, choice.value) if isinstance(choice, enum) else choice
                for choice in self.choices]
        else:
            self.choices = [(em.name, em.value) for em in enum]

        self._enum = enum

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['enum_type'] = self.enum_type
        if not self.manual_choices and 'choices' in kwargs:
            del kwargs['choices']
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
            return self.enum(str(value))
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
        if self.choices is True:
            return [(em.name, em.value) for em in self.enum]
        return super().get_choices(include_blank, blank_choice, limit_choices_to)

    # db_type method not needed if parameters set
    def db_type_parameters(self, connection):
        paras = super().db_type_parameters(connection)
        if connection.features.has_enum:
            paras['enum_type'] = self.enum_type
            paras['values'] = ', '.join('%s' * len(self.enum))
        return paras

    def db_type(self, connection):
        type_string = super().db_type(connection)
        values = None
        if connection.features.has_enum and not connection.features.requires_enum_declaration:
            values = [em.value for em in self.enum]

        return DBType(
            type_string,
            values)
