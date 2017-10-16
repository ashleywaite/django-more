
import logging
from contextlib import suppress
from django.utils.functional import cached_property
# Project imports
from patchy import patchy
from django.db.migrations.state import StateApps as DjangoStateApps

logger = logging.getLogger(__name__)


# Make types available via StateApps (not regular Apps)
class StateApps(DjangoStateApps):
    def __init__(self, *args, db_types=None, **kwargs):
        self.db_types = db_types or {}
        #print('StateApps for db_types')
        self.__init__.__patched__(self, *args, **kwargs)


class ProjectState:
    def __init__(self, *args, **kwargs):
        self.__init__.__patched__(self, *args, **kwargs)
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
        new_state = self.clone.__patched__(self)
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
        print('ALTER')
        new_type, params = self.column_sql_paramatized(new_type)
        print('alter', new_type, 'with', params)
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


class AddField:
    def state_forwards(self, app_label, state):
        # Inject make_live to ensure valid stateful version of type available
        if hasattr(self.field, 'make_live'):
            self.field.make_live(state)
        self.state_forwards.__patched__(self, app_label, state)


class CreateModel:
    def state_forwards(self, app_label, state):
        # Inject make_live to ensure valid stateful version of type available
        for field in self.fields:
            if hasattr(field, 'make_live'):
                field.make_live(state)
        self.state_forwards.__patched__(self, app_label, state)


class AlterField:
    def state_forwards(self, app_label, state):
        # Inject make_live to ensure valid stateful version of type available
        if hasattr(self.field, 'make_live'):
            self.field.make_live(state)
        self.state_forwards.__patched__(self, app_label, state)


def patch_types():
    logger.info('Applying django_types patches')

    # Patch migration classes to statefully apply types
    with patchy('django.db.migrations.state') as p:
        with p.cls('ProjectState', ProjectState) as c:
            c.add('__init__', 'add_type', 'remove_type', 'clone')
            c.add_desc('apps')
        with p.cls('StateApps', StateApps) as c:
            c.add('__init__')
        #p.cls('operations.fields.AddField', AddField).auto()
        #p.cls('operations.fields.AlterField', AlterField).auto()
        #p.cls('operations.models.CreateModel', CreateModel).auto()

    # Patch backend classes to allow parametised db_types
    with patchy('django.db.backends.base.schema.BaseDatabaseSchemaEditor', BaseDatabaseSchemaEditor) as c:
        c.auto()
        c.add('_alter_column_type_sql')
