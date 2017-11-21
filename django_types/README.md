# django_types

Provides a base implemention for custom database types in Django 1.11+.  
It tracks data types within the migration state and migration apps so that fields relying on these can more easily hook into auto-migration, and have stateful field instances appropriate for prior states of the project.


## CustomTypeField

The CustomTypeField requires only the type_name, which should uniquely identify it regardless of app_labels, and be used as the database type name where possible.
This is what should be use with migrations to track the state of the type and act accordingly.

The type_def is an implementation class for the type represented, and should be set by subclasses upon instantiation, and will be retrieved via the app state during migrations, so should never be included in deconstruct() or other stateful methods.

Type implementation classes that contain a Meta can override the database type and app_label that will be used.
Where not provided, the default is to generate a type name based upon the app the class is contained within, and the name of the implementation class.

_contribute_to_class()_ provides the hooks to regain previous states during migration and make the field actually operable in that state, based on the type_name.

_clone()_ will copy the type_def where it exists, so that stateful fields remain stateful through model/field cloning, especially during migration.


## DBType

Also used is an overloaded _str_ class that allows for the use of parametised values in places where Django doesn't otherwise support them, such as in the db_type. (ie, this is necessary for enum usage on mysql)


## Django patches

Changes to Django that are necessary are applied by _patch_types()_
This should be called by any app that requires custom types.

### Custom types
Patches to make custom types work.

**ProjectState** _(django.db.migrations.state.ProjectState)_  
Modified to store custom types that may be relevant to the database, and ensure that apps objects based on this state also have them available.
*   **\_\_init\_\_( \* )**: Also initialises _db_types_ dict.
*   **apps**: Will pass through _db_types_ when creating `StateApps`.
*   **add_type(self, type_name, type_def, app_label)**: Add a new type to the local _db_types_ and if _apps_ exists to there too.
*   **remove_type(self, type_name)**: Remove a type from _db_types_ and if _apps_ exists from there too.
*   **clone(self)**: Also clones _db_types_ and _apps.db_types__.

**StateApps** _(django.db.migrations.state.StateApps)_  
*   **\_\_init\_\_( \* )**: Accepts _db_types_ keyword argument.

**BaseDatabaseSchemaEditor** _(django.db.backends.base.schema.BaseDatabaseSchemaEditor)_
*   **column_sql_paramatized(self, col_type)**: Convenience method to turn any valid _col_type_ into an `sql, params` pair.
*   **\_alter_column_type_sql()**: Changed to support parametised DBTypes.
*   **\_column_sql()**: Changed to support parametised DBTypes.

### Field dependencies
Patches to make field based dependencies work.

**Field** _(django.db.models.Field)_
*   **has_dependencies**: New flag that defaults to False.  
*   **dependencies**: _cached_property_ of what is given by _get_dependencies()_.
*   **get_dependencies()**: Skeleton that returns an empty list, so inherited classes can always use `super()`.

**RelatedField** _(django.db.models.fields.related.RelatedField)_
*   **has_dependencies**: Flag set to True.
*   **get_dependencies()**: will return the list of dependencies this field has, performing the same function as `MigrationAutodetector._get_dependencies_for_foreign_key(field)` would for any existing foreign key types.

**MigrationAutodetector** _(django.db.migrations.autodetector.MigrationAutodetector)_
*   **generate_created_models()**: Changed to use field based dependencies logic.
*   **\_generate_added_field()**: Changed to use field based dependencies logic.
*   **\_generate_altered_foo_together()**: Changed to use field based dependencies logic.
