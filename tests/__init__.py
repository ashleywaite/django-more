
from django.core.exceptions import ValidationError
from django.test import TestCase


class FieldTestCase(TestCase):

    def assertFieldValue(self, fieldclass, valid, invalid, field_args=None, field_kwargs=None):
        field_args = field_args or []
        field_kwargs = field_kwargs or {}
        field = fieldclass(*field_args, **field_kwargs)

        for input, output in valid.items():
            self.assertEqual(field.clean(input, None), output)

        for input, errors in invalid.items():
            with self.assertRaisesRegex(ValidationError, errors):
                field.clean(input, None)
