""" Container classes for methods and attributes to be patched into django """
from itertools import chain
from django.db import models
from django.db.migrations import operations
from django.db.migrations.state import StateApps as DjangoStateApps
from django.db.models.fields.related import RelatedField as DjangoRelatedField
from django.utils import six
from django.utils.functional import cached_property
# Project imports
from patchy import super_patchy
from .utils import dependency_tuple

# Methods replaced in whole:
# CHANGED indicates block of changed code from original
# < lines that were removed or changed are commented out with <
# XXX indicates end of replaced block


# Make types available via StateApps (not regular Apps)
class StateApps:
    def __init__(self, *args, db_types=None, **kwargs):
        self.db_types = db_types or {}
        super_patchy(*args, **kwargs)


class Field:
    # Ensure all fields have a dependencies flag
    has_dependencies = False

    @cached_property
    def dependencies(self):
        return self.get_dependencies()

    def get_dependencies(self):
        return []


class RelatedField(models.Field):
    has_dependencies = True

    def get_dependencies(self):
        # Generate the default dependencies for a related field
        dependencies = super(DjangoRelatedField, self).get_dependencies()

        if self.remote_field:
            # Account for FKs to swappable models
            swappable_setting = getattr(self, 'swappable_setting', None)
            if swappable_setting is not None:
                dep_app_label = "__setting__"
                dep_object_name = swappable_setting
            else:
                dep_app_label = self.remote_field.model._meta.app_label
                dep_object_name = self.remote_field.model._meta.object_name
            # Depend on the model that this refers to
            dependencies.append(dependency_tuple(
                app_label=dep_app_label,
                object_name=dep_object_name,
                field=None,
                created=True))
            # And any manually declared through model
            if getattr(self.remote_field, 'through', None) and not self.remote_field.through._meta.auto_created:
                dependencies.append(dependency_tuple(
                    app_label=self.remote_field.through._meta.app_label,
                    object_name=self.remote_field.through._meta.object_name,
                    field=None,
                    created=True))
        return dependencies


# Make fields able to declare arbitrary dependencies
class MigrationAutodetector:

    def generate_created_models(self):
        """
        Find all new models (both managed and unmanaged) and make create
        operations for them as well as separate operations to create any
        foreign key or M2M relationships (we'll optimize these back in later
        if we can).
        We also defer any model options that refer to collections of fields
        that might be deferred (e.g. unique_together, index_together).
        """
        old_keys = set(self.old_model_keys).union(self.old_unmanaged_keys)
        added_models = set(self.new_model_keys) - old_keys
        added_unmanaged_models = set(self.new_unmanaged_keys) - old_keys
        all_added_models = chain(
            sorted(added_models, key=self.swappable_first_key, reverse=True),
            sorted(added_unmanaged_models, key=self.swappable_first_key, reverse=True)
        )
        for app_label, model_name in all_added_models:
            model_state = self.to_state.models[app_label, model_name]
            model_opts = self.new_apps.get_model(app_label, model_name)._meta
            # CHANGED
            # < # Gather related fields
            # < related_fields = {}
            # < primary_key_rel = None
            # < for field in model_opts.local_fields:
            # <     if field.remote_field:
            # <         if field.remote_field.model:
            # <             if field.primary_key:
            # <                 primary_key_rel = field.remote_field.model
            # <             elif not field.remote_field.parent_link:
            # <                 related_fields[field.name] = field
            # <         # through will be none on M2Ms on swapped-out models;
            # <         # we can treat lack of through as auto_created=True, though.
            # <         if (getattr(field.remote_field, "through", None) and
            # <                 not field.remote_field.through._meta.auto_created):
            # <             related_fields[field.name] = field
            # < for field in model_opts.local_many_to_many:
            # <     if field.remote_field.model:
            # <         related_fields[field.name] = field
            # <     if getattr(field.remote_field, "through", None) and not field.remote_field.through._meta.auto_created:
            # <         related_fields[field.name] = field
            # Generate dict of fields with dependencies (excluding primary key)
            dependent_fields = {
                field.name: field
                for field in chain(model_opts.local_fields, model_opts.local_many_to_many)
                if field.has_dependencies and not field.primary_key}
            # XXX

            # Are there indexes/unique|index_together to defer?
            indexes = model_state.options.pop('indexes')
            unique_together = model_state.options.pop('unique_together', None)
            index_together = model_state.options.pop('index_together', None)
            order_with_respect_to = model_state.options.pop('order_with_respect_to', None)
            # Depend on the deletion of any possible proxy version of us
            dependencies = [
                # CHANGED
                # < (app_label, model_name, None, False),
                dependency_tuple(app_label=app_label, object_name=model_name, field=None, created=False),
                # XXX
            ]
            # Depend on all bases
            for base in model_state.bases:
                if isinstance(base, six.string_types) and "." in base:
                    base_app_label, base_name = base.split(".", 1)
                    # CHANGED
                    # < dependencies.append((base_app_label, base_name, None, True))
                    dependencies.append(dependency_tuple(base_app_label, base_name, None, True))
                    # XXX
            # Depend on the other end of the primary key if it's a relation
            # CHANGED
            # < if primary_key_rel:
            # <     dependencies.append((
            # <         primary_key_rel._meta.app_label,
            # <         primary_key_rel._meta.object_name,
            # <         None,
            # <         True
            # <     ))
            if model_opts.pk.remote_field:
                dependencies.append(dependency_tuple(
                    app_label=model_opts.pk.remote_field.model._meta.app_label,
                    object_name=model_opts.pk.remote_field.model._meta.object_name,
                    field=None,
                    created=True))
            # XXX
            # Generate creation operation
            self.add_operation(
                app_label,
                operations.CreateModel(
                    name=model_state.name,
                    # CHANGED
                    # < fields=[d for d in model_state.fields if d[0] not in related_fields],
                    fields=[d for d in model_state.fields if d[0] not in dependent_fields],
                    # XXX
                    options=model_state.options,
                    bases=model_state.bases,
                    managers=model_state.managers,
                ),
                dependencies=dependencies,
                beginning=True,
            )

            # Don't add operations which modify the database for unmanaged models
            if not model_opts.managed:
                continue

            # CHANGED
            # Dependency for this model
            model_dependency = dependency_tuple(app_label=app_label, object_name=model_name, field=None, created=True)
            # < # Generate operations for each related field
            # < for name, field in sorted(related_fields.items()):
            # <     dependencies = self._get_dependencies_for_foreign_key(field)
            # <     # Depend on our own model being created
            # <     dependencies.append((app_label, model_name, None, True))
            # <     # Make operation
            # <     self.add_operation(
            # <         app_label,
            # <         operations.AddField(
            # <             model_name=model_name,
            # <             name=name,
            # <             field=field,
            # <         ),
            # <         dependencies=list(set(dependencies)),
            # <     )
            # Generate operations for each dependent field
            for name, field in sorted(dependent_fields.items()):
                # Make operation
                self.add_operation(
                    app_label,
                    operations.AddField(
                        model_name=model_name,
                        name=name,
                        field=field),
                    dependencies=list(set(field.dependencies + [model_dependency])))
            # < # Generate other opns
            # < related_dependencies = [
            # <     (app_label, model_name, name, True)
            # <     for name, field in sorted(related_fields.items())
            # < ]
            # Generate a dependency for each field with dependencies (as any may be deferred)
            field_dependencies = [
                dependency_tuple(app_label=app_label, object_name=model_name, field=name, created=True)
                for name, field in sorted(dependent_fields.items())]
            # < related_dependencies.append((app_label, model_name, None, True))
            field_dependencies.append(model_dependency)
            # XXX
            for index in indexes:
                self.add_operation(
                    app_label,
                    operations.AddIndex(
                        model_name=model_name,
                        index=index,
                    ),
                    # CHANGED
                    # < dependencies=related_dependencies
                    dependencies=field_dependencies,
                    # XXX
                )
            if unique_together:
                self.add_operation(
                    app_label,
                    operations.AlterUniqueTogether(
                        name=model_name,
                        unique_together=unique_together,
                    ),
                    # CHANGED
                    # < dependencies=related_dependencies
                    dependencies=field_dependencies,
                    # XXX
                )
            if index_together:
                self.add_operation(
                    app_label,
                    operations.AlterIndexTogether(
                        name=model_name,
                        index_together=index_together,
                    ),
                    # CHANGED
                    # < dependencies=related_dependencies
                    dependencies=field_dependencies,
                    # XXX
                )
            if order_with_respect_to:
                self.add_operation(
                    app_label,
                    operations.AlterOrderWithRespectTo(
                        name=model_name,
                        order_with_respect_to=order_with_respect_to,
                    ),
                    dependencies=[
                        # CHANGED
                        # < (app_label, model_name, order_with_respect_to, True),
                        # < (app_label, model_name, None, True),
                        dependency_tuple(app_label, model_name, order_with_respect_to, True),
                        model_dependency,
                        # XXX
                    ]
                )

            # Fix relationships if the model changed from a proxy model to a
            # concrete model.
            if (app_label, model_name) in self.old_proxy_keys:
                for related_object in model_opts.related_objects:
                    self.add_operation(
                        related_object.related_model._meta.app_label,
                        operations.AlterField(
                            model_name=related_object.related_model._meta.object_name,
                            name=related_object.field.name,
                            field=related_object.field,
                        ),
                        # CHANGED
                        # < dependencies=[(app_label, model_name, None, True)],
                        dependencies=[model_dependency],
                        # XXX
                    )

    # Replace dependency test and just pass field dependencies directly
    def _generate_added_field(self, app_label, model_name, field_name):
        field = self.new_apps.get_model(app_label, model_name)._meta.get_field(field_name)
        # You can't just add NOT NULL fields with no default or fields
        # which don't allow empty strings as default.
        # CHANGED
        # < # Fields that are foreignkeys/m2ms depend on stuff
        # < dependencies = []
        # < if field.remote_field and field.remote_field.model:
        # <     dependencies.extend(self._get_dependencies_for_foreign_key(field))
        # XXX
        preserve_default = True
        time_fields = (models.DateField, models.DateTimeField, models.TimeField)
        if (not field.null and not field.has_default() and
                not field.many_to_many and
                not (field.blank and field.empty_strings_allowed) and
                not (isinstance(field, time_fields) and field.auto_now)):
            field = field.clone()
            if isinstance(field, time_fields) and field.auto_now_add:
                field.default = self.questioner.ask_auto_now_add_addition(field_name, model_name)
            else:
                field.default = self.questioner.ask_not_null_addition(field_name, model_name)
            preserve_default = False
        self.add_operation(
            app_label,
            operations.AddField(
                model_name=model_name,
                name=field_name,
                field=field,
                preserve_default=preserve_default,
            ),
            # CHANGED
            # < preserve_default=preserve_default,
            dependencies=field.dependencies,
            # XXX
        )

    # Replace dependencies logic
    def _generate_altered_foo_together(self, operation):
        option_name = operation.option_name
        for app_label, model_name in sorted(self.kept_model_keys):
            old_model_name = self.renamed_models.get((app_label, model_name), model_name)
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]

            # We run the old version through the field renames to account for those
            old_value = old_model_state.options.get(option_name) or set()
            if old_value:
                old_value = {
                    tuple(
                        self.renamed_fields.get((app_label, model_name, n), n)
                        for n in unique
                    )
                    for unique in old_value
                }

            new_value = new_model_state.options.get(option_name) or set()
            if new_value:
                new_value = set(new_value)

            if old_value != new_value:
                dependencies = []
                for foo_togethers in new_value:
                    for field_name in foo_togethers:
                        field = self.new_apps.get_model(app_label, model_name)._meta.get_field(field_name)
                        # CHANGED
                        # < if field.remote_field and field.remote_field.model:
                        # <     dependencies.extend(self._get_dependencies_for_foreign_key(field))
                        if field.has_dependencies:
                            dependencies.extend(field.dependencies)
                        # XXX

                self.add_operation(
                    app_label,
                    operation(
                        name=model_name,
                        **{option_name: new_value}
                    ),
                    dependencies=dependencies,
                )


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
