
from django_more import NullCharField
from .models import NullCharModel
from . import FieldTestCase


class NullCharFieldTest(FieldTestCase):

    def test_save_null_is_null(self):
        record = NullCharModel()
        record.test_field = None
        record.save()
        record = NullCharModel.objects.get(pk=record.pk)
        self.assertIsNone(record.test_field)

    def test_save_blank_is_null(self):
        record = NullCharModel()
        record.test_field = ''
        record.save()
        record = NullCharModel.objects.get(pk=record.pk)
        self.assertIsNone(record.test_field)

    def test_save_value_is_unaffected(self):
        record = NullCharModel()
        record.test_field = 'abc'
        record.save()
        record = NullCharModel.objects.get(pk=record.pk)
        self.assertEqual(record.test_field, 'abc')

    def test_value_conversions(self):
        self.assertFieldValue(
            fieldclass=NullCharField,
            valid={
                'abc': 'abc',
                '': None,
                None: None},
            invalid={},
            field_kwargs={'max_length': 10})
