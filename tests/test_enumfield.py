""" Run tests related to django_enum.EnumField """
from enum import Enum
# Framework imports
from django.core.exceptions import ValidationError
from django.db.models.fields import BLANK_CHOICE_DASH
from django.test import TestCase
from django_enum import EnumField
from .models import TestEnum, WrongEnum, MetaEnum


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
                'VAL1': 'not in enumeration',
                'VAL2': 'not in enumeration',
                '': 'not in enumeration',
                'None':  'not in enumeration',
                WrongEnum.VAL1: 'incompatible enumeration',
                WrongEnum.VAL3: 'incompatible enumeration',
                1: 'not an enum member or string',
                -5:  'not an enum member or string',
                123: 'not an enum member or string',
                (): 'not an enum member or string',
                None: 'cannot be null'},
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
                123: 'not an enum member or string',
                WrongEnum.VAL1: 'incompatible enumeration',
                WrongEnum.VAL3: 'incompatible enumeration'},
            field_args=[TestEnum],
            field_kwargs={'case_sensitive': False})

    def test_default_choices(self):
        field = EnumField(TestEnum)
        choices = field.get_choices(blank_choice=BLANK_CHOICE_DASH)
        expected = BLANK_CHOICE_DASH + [(em, em.value) for em in TestEnum]
        self.assertEqual(choices, expected)

    def test_manual_choices(self):
        members = [TestEnum.VAL1, TestEnum.VAL2]
        field = EnumField(TestEnum, choices=members)
        choices = field.get_choices(blank_choice=BLANK_CHOICE_DASH)
        expected = BLANK_CHOICE_DASH + [(em, em.value) for em in members]
        self.assertEqual(choices, expected)
