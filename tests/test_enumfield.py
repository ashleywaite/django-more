""" Run tests related to django_enum.EnumField """
from enum import Enum
# Framework imports
from django.core.exceptions import ValidationError
from django.db.models.fields import BLANK_CHOICE_DASH
from django.test import TestCase
from django_enum import EnumField, enum_meta


class TestEnum(Enum):
    VAL1 = 'The first value'
    VAL2 = 'The second value'
    VAL3 = 'Third value is the best'


class WrongEnum(Enum):
    VAL1 = 'The first wrong value'
    VAL2 = 'Another one wrong'
    VAL3 = 'Third value is the best'


class MetaEnum(Enum):
    VAL1 = 'First meta value'
    VAL2 = 'So meta'
    VAL3 = 'Third value is the best'
    @enum_meta
    class Meta:
        db_type = 'test_enum_meta'


class EnumFieldTest(TestCase):
    multi_db = True

    def assertFieldValue(self, fieldclass, valid, invalid, field_args=None, field_kwargs=None):
        field_args = field_args or []
        field_kwargs = field_kwargs or {}
        field = fieldclass(*field_args, **field_kwargs)

        for input, output in valid.items():
            self.assertEqual(field.clean(input, None), output)

        for input, errors in invalid.items():
            with self.assertRaisesRegex(ValidationError, errors) as context_manager:
                field.clean(input, None)


    def test_create(self):
        field = EnumField(TestEnum)

        self.assertEqual(field.type_def, TestEnum)

    def test_assignment(self):
        field = EnumField(TestEnum)

        self.assertFieldValue(
            fieldclass=EnumField,
            valid={
                'The first value': TestEnum.VAL1,
                'The second value': TestEnum.VAL2,
                'Third value is the best': TestEnum.VAL3,
                TestEnum.VAL1: TestEnum.VAL1,
                TestEnum.VAL2: TestEnum.VAL2,
                TestEnum.VAL3: TestEnum.VAL3},
            invalid={
                'The invalid value': 'not in enumeration',
                123: 'not in enumeration',
                WrongEnum.VAL1: 'not in enumeration',
                WrongEnum.VAL3: 'not in enumeration'},
            field_args=[TestEnum])

    def test_meta_not_member(self):
        field = EnumField(MetaEnum)

        self.assertEqual(
            dict(MetaEnum.__members__),
            {
                'VAL1': MetaEnum.VAL1,
                'VAL2': MetaEnum.VAL2,
                'VAL3': MetaEnum.VAL3
            })

    def test_case_insensitive(self):
        self.assertFieldValue(
            fieldclass=EnumField,
            valid={
                'THE FIRST VALUE': TestEnum.VAL1,
                'the second value': TestEnum.VAL2,
                'ThirD vaLue IS the bEst': TestEnum.VAL3},
            invalid={
                'The invalid value': 'not in enumeration',
                123: 'not in enumeration',
                WrongEnum.VAL1: 'not in enumeration',
                WrongEnum.VAL3: 'not in enumeration'},
            field_args=[TestEnum],
            field_kwargs={'case_sensitive': False})

    def test_default_choices(self):
        field = EnumField(TestEnum)

        self.assertEqual(
            field.get_choices(blank_choice=BLANK_CHOICE_DASH),
            BLANK_CHOICE_DASH + [(em, em.value) for em in TestEnum]
        )
