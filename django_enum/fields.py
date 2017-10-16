from contextlib import suppress
from enum import Enum

from django.db import models
from django.db.models import BLANK_CHOICE_DASH
from django.core.exceptions import ValidationError
from django_types import CustomTypeField, DBType

__all__ = ['EnumField']


class EnumField(CustomTypeField):
    description = 'Enumeration field using python PEP435 and database implementations'
    case_sensitive = None
    manual_choices = False
    type_def_subclass = Enum

    data_types = {
        'unknown': models.CharField,
        'postgresql': '%(type_name)s',
        'mysql': 'enum(%(values)s)',
    }

    def __init__(self, enum=None, case_sensitive=None, **kwargs):
        super().__init__(**kwargs)
        if kwargs.get('choices', False):
            self.manual_choices = True
        if enum:
            self.type_def = enum
        if case_sensitive is not None:
            self.case_sensitive = case_sensitive

    # Add choices generation to type_def setting
    @CustomTypeField.type_def.setter
    def type_def(self, enum):
        CustomTypeField.type_def.fset(self, enum)

        # Allow enum members as choices
        if self.manual_choices:
            self.choices = [
                (choice.name, choice.value) if isinstance(choice, self.type_def) else choice
                for choice in self.choices]
        else:
            self.choices = [(em.name, em.value) for em in self.type_def]

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if not self.manual_choices and 'choices' in kwargs:
            del kwargs['choices']
        if self.case_sensitive is not None:
            kwargs['case_sensitive'] = self.case_sensitive
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return None
        with suppress(KeyError):
            return self.type_def(str(value))
        raise ValueError('Invalid enumeration value returned from database')

    def to_python(self, value):
        if value is None or isinstance(value, self.type_def):
            return value
        with suppress(ValueError):
            return self.type_def(str(value))
        # Enum match failed, if not case_sensitive, try insensitive scan
        if self.case_sensitive is False:
            for em in self.type_def:
                if str(value).lower() == em.value.lower():
                    return em
        raise ValidationError('Invalid enumeration value')

    def get_prep_value(self, value):
        if not value:
            return value
        if not isinstance(value, self.type_def):
            value = self.to_python(value)
        return value.value

    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH, limit_choices_to=None):
        if self.choices is True:
            return [(em.name, em.value) for em in self.type_def]
        return super().get_choices(include_blank, blank_choice, limit_choices_to)

    def db_type_parameters(self, connection):
        paras = super().db_type_parameters(connection)
        paras.update(
            values=', '.join(['%s'] * len(self.type_def)),
            max_length=20)
        return paras

    def db_type(self, connection):
        type_string = super().db_type(connection)

        # Use overloaded str DBType to pass parametised version where possible
        values = None
        if connection.features.has_enum and not connection.features.requires_enum_declaration:
            values = [str(em.value) for em in self.type_def]

        return DBType(
            type_string,
            values)
