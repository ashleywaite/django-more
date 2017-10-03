
from enum import Enum
from contextlib import suppress, contextmanager

from django.db.migrations.operations.fields import Operation, FieldOperation, AlterField
from patchy import quick_patchy

"""
    Use a symbol = value style as per Enum expectations.
    Where a value is the human readable or sensible value, and the symbol is the
     constant or programming flag to use.
    For readbility of the database values, the human readable values are used.

"""

# Functions that apply patches if necessary
def patch_state(state):
    if hasattr(state, 'add_enum'):
        # Do not patch
        return False

    state.enums = []
    return True

def patch_questioner(questioner):
    if hasattr(questioner, 'ask_rename_enum'):
        # Do not patch
        return False

    return True


class MigrationAutodetector:

    def detect_enums(self):
        # Scan both state trees for enums
        old_enum_types = set(db_type for db_type, e in from_state.db_types.items() if isinstance(e, Enum))
        new_enum_types = set(db_type for db_type, e in to_state.db_types.items() if isinstance(e, Enum))

        # Look for renamed enums
        new_enum_sets = {k: set(em.value for em in self.to_state.db_types[k]) for k in new_enum_types - old_enum_types}
        old_enum_sets = {k: set(em.value for em in self.from_state.db_types[k]) for k in old_enum_types - new_enum_types}
        for db_type, enum_set in new_enum_sets.items():
            for rem_db_type, rem_enum_set in old_enum_sets.items():
                # Compare only the values
                if enum_set == rem_enum_set:
                    self.questioner.ask_rename_enum(db_type, rem_db_type):
                        self.add_operation(
                            RenameEnum(
                                old_type=rem_db_type,
                                new_type=db_type))
                        old_enum_sets.remove(rem_db_type)
                        new_enum_sets.remove(db_type)
                    break

        # Create new enums
        for db_type, values in new_enum_sets.items():
            self.add_operation(
                CreateEnum(
                    db_type=db_type,
                    values=values))

        # Remove old enums
        for db_type in old_enum_sets:
            self.add_operation(
                RemoveEnum(
                    db_type=db_type)

        # TODO Detect modified enums




class CreateEnum(Operation):
    def __init__(self, db_type, values):
        # Values follow Enum functional API options to specify
        self.db_type = db_type
        self.values = values

    def describe(self):
        return 'Creates an enum type {}'.format("")

    def state_forwards(self, app_label, state):
        enum = Enum(self.name, values)
        state.add_type(self.db_type, enum)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.features.requires_enum_declaration:
            enum = to_state.db_types[db_type]
            sql = schema_editor.sql_create_enum % {
                'enum_type': self.db_type,
                'choices': [','.join(['%s'] * len(self.values))]}
            schema_editor.execute(sql, tuple(v for v in self.values))

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
                'choices': [','.join(['%s'] * len(enum))]}
            schema_editor.execute(sql, tuple(em.value for em in enum))


class RenameEnum(Operation):
    def __init__(self, old_type, new_type, fields_dependent=None):
        self.old_db_type = old_db_type
        self.new_db_type = new_db_type
        self.fields = fields_dependent or set()

    def state_forwards(self, app_label, state):
        enum = state.db_types[self.old_db_type]
        state.add_type(self.new_db_type, enum)
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
