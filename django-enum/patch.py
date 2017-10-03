import sys
# Framework imports
import django
# Project imports
from patchy import patchy


# Containers for patched methods added with patchy
class ProjectState:
    def add_type(self, db_type, type_state):
        if not hasattr(self, 'db_types'):
            self.db_types = {}
        self.db_types[db_type] = type_state

    def remove_type(self, db_type):
        if hasattr(self, 'db_types'):
            del self.db_types[db_type]

    def clone(self):
        # Clone db_types state as well
        new_state = self.clone.__patched__(self)
        if hasattr(self, 'db_types'):
            new_state.db_types = {k: v.clone() for k, v in self.db_types.items()}
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
    sql_create_enum = 'CREATE TYPE {enum_type} AS ENUM ({choices})'
    sql_delete_enum = 'DROP TYPE {enum_type}'
    # ALTER TYPE for schema changes. pg9.1+ only
    # https://www.postgresql.org/docs/9.1/static/sql-altertype.html
    sql_alter_enum = 'ALTER TYPE {enum_type} ADD VALUE {value} {condition}'
    sql_rename_enum = 'ALTER TYPE {old_type} RENAME TO {enum_type}'
    # remove_from_enum is not supported by poostgres


def patch_enum():
    # Patch migrations classes
    with patchy('django.db.migrations') as p:
        # add_type, remove_type, clone
        p.cls('state.ProjectState', ProjectState).auto()
        # ask_rename_enum
        p.cls('questioner.MigrationQuestioner', MigrationQuestioner).auto()

    # Patch backend features
    with patchy('django.db.backends') as p:
        p.cls('base.features.BaseDatabaseFeatures', BaseDatabaseFeatures).auto()

        # Only patch database backends in use (avoid dependencies)
        if 'django.db.backends.postgresql' in sys.modules:
            p.cls('postgresql.features.DatabaseFeatures', PostgresDatabaseFeatures).auto()
            p.cls('postgresql.schema.DatabaseSchemaEditor', PostgresDatabaseSchemaEditor).auto()
            p.cls('postgresql.base.DatabaseWrapper').merge('data_types', {'EnumField': '%(enum_type)'})

        if 'django.db.backends.mysql' in sys.modules:
            p.cls('mysql.features.DatabaseFeatures', MysqlDatabaseFeatures).auto()
            p.cls('mysql.base.DatabaseWrapper').merge('data_types', {'EnumField': 'enum(%(choices)))'})
