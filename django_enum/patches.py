""" Container classes for methods and attributes to be patched into django """
from enum import Enum
# Framework imports
from django.db import models
# Project imports
from django_types.utils import find_fields
from patchy import super_patchy
from .operations import CreateEnum, RemoveEnum, RenameEnum, AlterEnum, enum_state
from .fields import EnumField


class MigrationQuestioner:
    def ask_rename_enum(self, old_enum_key, new_enum_key, enum_set):
        return self.defaults.get('ask_rename_enum', False)

    def ask_remove_enum_values(self, db_type, values):
        return self.defaults.get('ask_remove_enum_values', None)


class InteractiveMigrationQuestioner:
    def ask_rename_enum(self, old_enum_key, new_enum_key, enum_set):
        return self._boolean_input(
            'Did you rename enum {old_key} to {new_key}? [y/N]'.format(
                old_key=old_enum_key,
                new_key=new_enum_key),
            default=False)

    def ask_remove_enum_values(self, db_type, values):
        """ How to treat records with deleted enum values. """
        # Ordered ensures
        choices = [
            (models.CASCADE, "Cascade - Delete records with removed values"),
            (models.PROTECT, "Protect - Block migrations if records contain removed values"),
            (models.SET_NULL, "Set NULL - Set value to NULL"),
            (models.SET_DEFAULT, "Set default - Set value to field default"),
            (models.SET, "Set value - Provide a one off default now"),
            (models.DO_NOTHING, "Do nothing - Consistency must be handled elsewhere"),
            (None, "Leave it to field definitions")]
        choice, _ = choices[self._choice_input(
            "Enum {db_type} has had {values} removed, "
            "existing records may need to be updated. "
            "Override update behaviour or do nothing and follow field behaviour.".format(
                db_type=db_type,
                values=values),
            [q for (k, q) in choices]) - 1]
        if choice == models.SET:
            return models.SET(self._ask_default())
        return choice


class BaseDatabaseFeatures:
    # Assume no database support for enums
    has_enum = False
    requires_enum_declaration = False


class PostgresDatabaseFeatures:
    # Django only supports postgres 9.3+, enums added in 8.3, assume supported
    has_enum = True
    # Identify that enums must be declared prior to use
    requires_enum_declaration = True


class MysqlDatabaseFeatures:
    # Supports inline declared enums
    has_enum = True
    requires_enum_declaration = False


class PostgresDatabaseSchemaEditor:
    # CREATE TYPE enum_name AS ENUM ('value 1', 'value 2')
    # https://www.postgresql.org/docs/9.1/static/datatype-enum.html
    sql_create_enum = 'CREATE TYPE %(enum_type)s AS ENUM (%(values)s)'
    sql_delete_enum = 'DROP TYPE %(enum_type)s'
    # ALTER TYPE for schema changes. pg9.1+ only
    # https://www.postgresql.org/docs/9.1/static/sql-altertype.html
    sql_alter_enum = 'ALTER TYPE %(enum_type)s ADD VALUE %(value)s %(condition)s'
    sql_rename_enum = 'ALTER TYPE %(old_type)s RENAME TO %(enum_type)s'
    # remove_from_enum is not supported by poostgres

    sql_alter_column_type_using = 'ALTER COLUMN %(column)s TYPE %(type)s USING (%(column)s::text::%(type)s)'


class MigrationAutodetector:

    def detect_enums(self):
        # Scan to_state new enums in use
        for info in find_fields(self.to_state, field_type=EnumField):
            if info.field.type_name not in self.to_state.db_types:
                self.to_state.add_type(info.field.type_name, enum_state(info.field.type_def, app_label=info.field.type_app_label))

        from_enum_types = set(db_type for db_type, e in self.from_state.db_types.items() if issubclass(e, Enum))
        to_enum_types = set(db_type for db_type, e in self.to_state.db_types.items() if issubclass(e, Enum))

        # Look for renamed enums
        new_enum_sets = {k: self.to_state.db_types[k].values_set() for k in to_enum_types - from_enum_types}
        old_enum_sets = {k: self.from_state.db_types[k].values_set() for k in from_enum_types - to_enum_types}
        for db_type, enum_set in list(new_enum_sets.items()):
            for rem_db_type, rem_enum_set in old_enum_sets.items():
                # Compare only the values
                if enum_set == rem_enum_set:
                    if self.questioner.ask_rename_enum(db_type, rem_db_type, enum_set):
                        self.add_operation(
                            self.to_state.db_types[db_type].Meta.app_label,
                            RenameEnum(old_type=rem_db_type, new_type=db_type),
                            beginning=True)
                        del old_enum_sets[rem_db_type]
                        del new_enum_sets[db_type]
                    break

        # Create new enums
        for db_type, values in new_enum_sets.items():
            self.add_operation(
                self.to_state.db_types[db_type].Meta.app_label,
                CreateEnum(db_type=db_type, values=list(values)),
                beginning=True)

        # Remove old enums
        for db_type in old_enum_sets:
            self.add_operation(
                self.from_state.db_types[db_type].Meta.app_label,
                RemoveEnum(db_type=db_type),
                beginning=True)

        # Does not detect renamed values in enum, that's a remove + add
        existing_enum_sets = {k: (
            self.from_state.db_types[k].values_set(),
            self.to_state.db_types[k].values_set())
            for k in from_enum_types & to_enum_types}
        for db_type, (old_set, new_set) in existing_enum_sets.items():
            if old_set != new_set:
                paras = {'db_type': db_type}
                removed = list(old_set - new_set)
                added = list(new_set - old_set)
                if removed:
                    paras['remove_values'] = removed
                    paras['on_delete'] = self.questioner.ask_remove_enum_values(db_type, removed)
                if added:
                    paras['add_values'] = added
                self.add_operation(
                    self.from_state.db_types[db_type].Meta.app_label,
                    AlterEnum(**paras),
                    beginning=True)

    # Better to do after model creation and then inject operations at front of list
    def generate_created_models(self, *args, **kwargs):
        super_patchy(*args, **kwargs)
        self.detect_enums()
