""" Container classes for methods and attributes to be patched into django """
from contextlib import suppress
from django.utils.functional import cached_property
# Project imports
from patchy import super_patchy
from django.db.migrations.state import StateApps as DjangoStateApps


# Make types available via StateApps (not regular Apps)
class StateApps:
    def __init__(self, *args, db_types=None, **kwargs):
        self.db_types = db_types or {}
        super_patchy(*args, **kwargs)


class ProjectState:
    def __init__(self, *args, **kwargs):
        super_patchy(*args, **kwargs)
        self.db_types = {}

    @cached_property
    def apps(self):
        return DjangoStateApps(self.real_apps, self.models, db_types=self.db_types.copy())

    def add_type(self, type_name, type_def, app_label=None):
        self.db_types[type_name] = type_def
        if 'apps' in self.__dict__:  # hasattr would cache the property
            self.apps.db_types[type_name] = type_def

    def remove_type(self, type_name):
        del self.db_types[type_name]
        if 'apps' in self.__dict__:  # hasattr would cache the property
            del self.apps.db_types[type_name]

    def clone(self):
        # Clone db_types state as well
        new_state = super_patchy()
        new_state.db_types = self.db_types.copy()
        if 'apps' in self.__dict__:  # hasattr would cache the property
            new_state.apps.db_types = self.apps.db_types.copy()
        return new_state


class BaseDatabaseSchemaEditor:
    def column_sql_paramatized(self, col_type):
        if hasattr(col_type, 'paramatized'):
            return col_type.paramatized
        else:
            return col_type, []

    # Cannot trivially insert logic around, so whole method replaced
    def column_sql(self, model, field, include_default=False):
        # Get the column's type and use that as the basis of the SQL
        db_params = field.db_parameters(connection=self.connection)
        sql, params = self.column_sql_paramatized(db_params['type'])
        # Check for fields that aren't actually columns (e.g. M2M)
        if sql is None:
            return None, None
        # Work out nullability
        null = field.null
        # If we were told to include a default value, do so
        include_default = include_default and not self.skip_default(field)
        if include_default:
            default_value = self.effective_default(field)
            if default_value is not None:
                if self.connection.features.requires_literal_defaults:
                    # Some databases can't take defaults as a parameter (oracle)
                    # If this is the case, the individual schema backend should
                    # implement prepare_default
                    sql += " DEFAULT %s" % self.prepare_default(default_value)
                else:
                    sql += " DEFAULT %s"
                    params += [default_value]
        # Oracle treats the empty string ('') as null, so coerce the null
        # option whenever '' is a possible value.
        if (field.empty_strings_allowed and not field.primary_key and
                self.connection.features.interprets_empty_strings_as_nulls):
            null = True
        if null and not self.connection.features.implied_column_null:
            sql += " NULL"
        elif not null:
            sql += " NOT NULL"
        # Primary key/unique outputs
        if field.primary_key:
            sql += " PRIMARY KEY"
        elif field.unique:
            sql += " UNIQUE"
        # Optionally add the tablespace if it's an implicitly indexed column
        tablespace = field.db_tablespace or model._meta.db_tablespace
        if tablespace and self.connection.features.supports_tablespaces and field.unique:
            sql += " %s" % self.connection.ops.tablespace_sql(tablespace, inline=True)
        # Return the sql
        return sql, params

    def _alter_column_type_sql(self, model, old_field, new_field, new_type):
        """ Test for a parametised type and treat appropriately """
        new_type, params = self.column_sql_paramatized(new_type)
        return (
            (
                self.sql_alter_column_type % {
                    "column": self.quote_name(new_field.column),
                    "type": new_type,
                },
                params,
            ),
            [],
        )
