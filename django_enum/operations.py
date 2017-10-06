
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
    def __init__(self, db_type, values):
        # Values follow Enum functional API options to specify
        self.db_type = db_type
        self.values = values

    def describe(self):
        return 'Creates an enum type {}'.format("")

    def state_forwards(self, app_label, state):
        enum = Enum(self.db_type, self.values)
        state.add_type(self.db_type, enum, app_label=app_label)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.features.requires_enum_declaration:
            enum = to_state.db_types[self.db_type]
            print('choices', ', '.join(['%s'] * len(self.values)))
            sql = schema_editor.sql_create_enum % {
                'enum_type': self.db_type,
            schema_editor.execute(sql, tuple(v for v in self.values))
                'values': ', '.join(['%s'] * len(enum))}

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.features.requires_enum_declaration:
            sql = schema_editor.sql_drop_enum % {
                'enum_type': self.db_type}
            schema_editor.execute(sql)


class RemoveEnum(Operation):
    def __init__(self, db_type):
        self.db_type = db_type

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
            schema_editor.execute(sql, tuple(em.value for em in enum))
                'values': ', '.join(['%s'] * len(enum))}


class RenameEnum(Operation):
    def __init__(self, old_type, new_type, fields_dependent=None):
        self.old_db_type = old_db_type
        self.new_db_type = new_db_type
        self.fields = fields_dependent or set()

    def state_forwards(self, app_label, state):
        enum = state.db_types[self.old_db_type]
        state.add_type(app_label, self.new_db_type, enum)
        state.remove_type(self.old_db_type)
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
