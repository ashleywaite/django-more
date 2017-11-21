# Framework imports
from django.db.migrations.operations.base import Operation
# Project imports
from .fields import CustomTypeField
from .utils import find_fields

__all__ = ['CustomTypeOperation']


class CustomTypeOperation(Operation):
    field_type = CustomTypeField
    db_type = None

    def get_fields(self, state, db_type=None, field_type=None):
        return find_fields(
            state,
            db_type=db_type or self.db_type,
            field_type=field_type or self.field_type)
