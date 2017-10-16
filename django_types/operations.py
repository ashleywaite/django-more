
from collections import namedtuple
# Framework imports
from django.db.migrations.operations.base import Operation
# Project imports
from .fields import CustomTypeField

__all__ = ['CustomTypeOperation', 'find_fields']


field_info = namedtuple('fielddetail', ['model_state', 'model_app_label', 'model_name', 'field', 'field_name', 'field_index'])

def find_fields(state, db_type=None, field_type=None):
    field_type = field_type or CustomTypeField
    # Scan state for custom types in use
    return (
        field_info(model_state, model_app_label, model_name, field, field_name, field_index)
        for (model_app_label, model_name), model_state in state.models.items()
        for field_index, (field_name, field) in enumerate(model_state.fields)
        if isinstance(field, field_type)
            and (field.type_name == db_type or not db_type))


class CustomTypeOperation(Operation):
    get_fields = staticmethod(find_fields)

    def make_all_live(self, state, db_type, field_type=None):
        # Update field states with live types
        type_def = state.db_types[db_type]
        for info in self.get_fields(state, db_type, field_type):
            info.field.make_live(state)
            state.reload_model(info.model_app_label, info.model_name)
