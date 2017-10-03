import sys
from enum import Enum
# Framework imports
import django
# Project imports
from patchy import patchy
from .operations import CreateEnum, RemoveEnum, RenameEnum
from .fields import EnumField


# Containers for patched methods added with patchy
class ProjectState:
    def init_types(self):
        if not hasattr(self, 'db_types'):
            self.db_types = {}
        if not hasattr(self, 'db_types_apps'):
            self.db_types_apps = {}

    def add_type(self, db_type, type_state, app_label=None):
        self.init_types()
        self.db_types[db_type] = type_state
        if app_label:
            self.db_types_apps[db_type] = app_label

    def remove_type(self, db_type):
        if hasattr(self, 'db_types'):
            del self.db_types[db_type]

    def clone(self):
        # Clone db_types state as well
        new_state = self.clone.__patched__(self)
        if hasattr(self, 'db_types'):
            new_state.db_types = self.db_types.copy()
            new_state.db_types_apps = self.db_types_apps.copy()
        return new_state


class MigrationQuestioner:
    def ask_rename_enum(self, old_enum_key, new_enum_key, enum_set):
        return self.defaults.get("ask_rename_enum", False)


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
    sql_create_enum = 'CREATE TYPE %(enum_type)s AS ENUM (%(choices)s)'
    sql_delete_enum = 'DROP TYPE %(enum_type)s'
    # ALTER TYPE for schema changes. pg9.1+ only
    # https://www.postgresql.org/docs/9.1/static/sql-altertype.html
    sql_alter_enum = 'ALTER TYPE %(enum_type)s ADD VALUE %(value)s %(condition)s'
    sql_rename_enum = 'ALTER TYPE %(old_type)s RENAME TO %(enum_type)s'
    # remove_from_enum is not supported by poostgres


class MigrationAutodetector:

    def detect_enums(self):
        # Ensure types available
        self.to_state.init_types()
        self.from_state.init_types()

        # Scan to_state new enums in use
        for (model_app_label, model_name), model_state in self.to_state.models.items():
            for index, (name, field) in enumerate(model_state.fields):
                if isinstance(field, EnumField) and field.enum_type not in self.to_state.db_types:
                    self.to_state.add_type(field.enum_type, field.enum, app_label=field.enum_app)

        old_enum_types = set(db_type for db_type, e in self.from_state.db_types.items() if issubclass(e, Enum))
        new_enum_types = set(db_type for db_type, e in self.to_state.db_types.items() if issubclass(e, Enum))

        # Look for renamed enums
        new_enum_sets = {k: set(em.value for em in self.to_state.db_types[k]) for k in new_enum_types - old_enum_types}
        old_enum_sets = {k: set(em.value for em in self.from_state.db_types[k]) for k in old_enum_types - new_enum_types}
        for db_type, enum_set in new_enum_sets.items():
            for rem_db_type, rem_enum_set in old_enum_sets.items():
                # Compare only the values
                if enum_set == rem_enum_set:
                    if self.questioner.ask_rename_enum(db_type, rem_db_type):
                        self.add_operation(
                            self.from_state.db_types_apps[db_type],
                            RenameEnum(
                                old_type=rem_db_type,
                                new_type=db_type))
                        old_enum_sets.remove(rem_db_type)
                        new_enum_sets.remove(db_type)
                    break

        # Create new enums
        for db_type, values in new_enum_sets.items():
            self.add_operation(
                self.to_state.db_types_apps[db_type],
                CreateEnum(
                    db_type=db_type,
                    values=list(values)))

        # Remove old enums
        for db_type in old_enum_sets:
            self.add_operation(
                self.from_state.db_types_apps[db_type],
                RemoveEnum(
                    db_type=db_type))

        # TODO Detect modified enums

    # Must do before models, so inject detect_enums via here
    def generate_created_models(self):
        self.detect_enums()
        self.generate_created_models.__patched__(self)


def patch_enum():
    # Patch migrations classes
    with patchy('django.db.migrations') as p:
        # add_type, remove_type, clone
        p.cls('state.ProjectState', ProjectState).auto()
        # ask_rename_enum
        p.cls('questioner.MigrationQuestioner', MigrationQuestioner).auto()
        # detect_enums
        p.cls('autodetector.MigrationAutodetector', MigrationAutodetector).auto()

    # Patch backend features
    with patchy('django.db.backends') as p:
        p.cls('base.features.BaseDatabaseFeatures', BaseDatabaseFeatures).auto()

        # Only patch database backends in use (avoid dependencies)
        if 'django.db.backends.postgresql' in sys.modules:
            p.cls('postgresql.features.DatabaseFeatures', PostgresDatabaseFeatures).auto()
            p.cls('postgresql.schema.DatabaseSchemaEditor', PostgresDatabaseSchemaEditor).auto()
            p.cls('postgresql.base.DatabaseWrapper').merge(data_types={'EnumField': '%(enum_type)s'})

        if 'django.db.backends.mysql' in sys.modules:
            p.cls('mysql.features.DatabaseFeatures', MysqlDatabaseFeatures).auto()
            p.cls('mysql.base.DatabaseWrapper').merge(data_types={'EnumField': 'enum(%(choices)s))'})
