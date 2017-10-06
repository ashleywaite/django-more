
from enum import Enum
from contextlib import suppress

from django.db.migrations.operations.fields import Operation, FieldOperation, AlterField

"""
    Use a symbol = value style as per Enum expectations.
    Where a value is the human readable or sensible value, and the symbol is the
     constant or programming flag to use.
    For readbility of the database values, the human readable values are used.
"""


class CreateEnum(Operation):
class EnumState:
    @classmethod
    def values(cls):
        return [em.value for em in cls]

    @classmethod
    def values_set(cls):
        return set(cls.values())


def enum_state(values, name=None, app_label=None):
    """ Create an EnumState representing the values or Enum """
    print(type(values))
    if isinstance(values, type) and issubclass(values, Enum):
        print('Making enum_state from', values, values.values() if hasattr(values, 'values') else '')
        if not name:
            name = values.__name__
        values = (em.value for em in values)
    elif not name:
        name = 'Unnamed Enum'
    e = Enum(name, [(v, v) for v in values], type=EnumState)
    e.Meta = type('Meta', (object,), {})
    e.Meta.app_label = app_label
    return e
    def __init__(self, db_type, values):
        # Values follow Enum functional API options to specify
        self.db_type = db_type
        self.values = values

    def describe(self):
        return 'Create enum type {db_type}'.format(db_type=self.db_type)

    def state_forwards(self, app_label, state):
        enum = enum_state(self.values, name=self.db_type, app_label=app_label)
        state.add_type(self.db_type, enum)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.features.requires_enum_declaration:
            enum = to_state.db_types[self.db_type]
            print('choices', ', '.join(['%s'] * len(self.values)))
            sql = schema_editor.sql_create_enum % {
                'enum_type': self.db_type,
                'values': ', '.join(['%s'] * len(enum))}
            schema_editor.execute(sql, enum.values())

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.features.requires_enum_declaration:
            sql = schema_editor.sql_drop_enum % {
                'enum_type': self.db_type}
            schema_editor.execute(sql)


class RemoveEnum(Operation):
    def __init__(self, db_type):
        self.db_type = db_type

    def describe(self):
        return 'Remove enum type {db_type}'.format(db_type=self.db_type)

    def state_forwards(self, app_label, state):
        # TODO Add dependency checking and cascades
        state.remove_type(db_type)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.features.requires_enum_declaration:
            sql = schema_editor.sql_delete_enum % {
                'enum_type': self.db_type}
            schema_editor.execute(sql)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.features.requires_enum_declaration:
            enum = to_state.db_types[self.db_type]
            sql = schema_editor.sql_create_enum % {
                'enum_type': self.db_type,
                'values': ', '.join(['%s'] * len(enum))}
            schema_editor.execute(sql, enum.values())


class RenameEnum(Operation):
    def __init__(self, old_type, new_type):
        self.old_db_type = old_type
        self.db_type = new_type

    def describe(self):
        return 'Rename enum type {old} to {new}'.format(
            old=self.old_db_type,
            new=self.db_type)

    def state_forwards(self, app_label, state):
        old_enum = state.db_types[self.old_db_type]
        enum = enum_state(old_enum, name=self.db_type, app_label=app_label)
        state.remove_type(self.old_db_type)
        state.add_type(self.db_type, enum)

        # Alter all fields using this enum
        for (model_app_label, model_name), model_state in state.models.items():
            for index, (name, field) in enumerate(model_state.fields):
                if isinstance(field, EnumField) and field.enum_type == self.old_db_type:
                    changed_field = field.clone()
                    changed_field.enum_type = self.new_db_type
                    model_state.fields[index] = name, changed_field
                    self.fields.add((model_app_label, model_name, name))

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.features.requires_enum_declaration:
            sql = schema_editor.sql_rename_enum % {
                'old_type': self.old_db_type,
                'enum_type': self.new_db_type}
            schema_editor.execute(sql)
            # Update fields referring to this enum
            for (model_app_label, model_name, name) in self.fields:
                model = from_state.models[(model_app_label, model_name)]
                schema_editor.sql_alter_column % {
                    'table': schema_editor.quote_name(model._meta.db_table),
                    'changes': schema_editor.sql_alter_column_type % {
                        'column': schema_editor.quote_name(name),
                        'type': self.new_db_type}}
                schema_editor.execute(sql)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self.old_db_type, self.new_db_type = self.new_db_type, self.old_db_type

        self.database_forwards(app_label, schema_editor, from_state, to_state)

        self.old_db_type, self.new_db_type = self.new_db_type, self.old_db_type


class AlterEnum(AlterField):

    def state_forwards(self, app_label, state):
        enum = state.db_types[old_db_type]
        state.add_type(new_db_type, enum)
        state.remove_type(old_db_type)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        # Compare from_state and to_state and generate the appropriate ALTER commands

        pass

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass
