from collections import namedtuple
from .fields import CustomTypeField


# Prettify declaration of dependencies
dependency_tuple = namedtuple('dependency_tuple', ['app_label', 'object_name', 'field', 'created'])


class DBType(str):
    """ Create a db_type string that can represent paramatised values """
    params = []
    db_type = None

    def __new__(cls, value, params=None, *args, **kwargs):
        if params:
            self = super().__new__(cls, cls.render(value, params))
            self.params = params
        else:
            self = super().__new__(cls, value)
        self.db_type = value
        return self

    @property
    def paramatized(self):
        return self.db_type, self.params

    @staticmethod
    def render(db_type, params):
        return db_type % tuple(params)


# Pretty tuple of field information
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
