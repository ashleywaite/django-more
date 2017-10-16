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

Changes to Django that are necessary are applied by _patch_enum()_
These are automatically applied via the app _ready()_ if you place django_enum into installed apps.

**ProjectState** (django.db.migrations.state.ProjectState)  
Modified to store custom types that may be relevant to the database, and ensure that apps objects based on this state also have them available.

**StateApps** (django.db.migrations.questioner.MigrationQuestioner)  
Modified to allow for db_types to be provided on __init__ so that fields created will have access to type implementation classes.

**BaseDatabaseSchemaEditor** (django.db.backends.base.schema.BaseDatabaseSchemaEditor)  
Modified _\_alter_column_type_sql()_ and _coloum_sql()_ to support parametised types.
