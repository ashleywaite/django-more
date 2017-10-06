# django_enum

Provides a cross-database implementation of an EnumField for Django 1.11+.
It treats new data types as a state of the project that need to be updated and modified at different stages,
so that versioning is consistent in older states - enforcing correct enum states at the time of that migration instead
of the current state of the enum in the project code.


## Django patches

Changes to Django that are necessary are applied by _patch_enum()_
These are automatically applied via the app _ready()_ if you place django_enum into installed apps.

**ProjectState** (django.db.migrations.state.ProjectState)  
Modified to store custom types that may be relevant to the database.

**MigrationQuestioner** (django.db.migrations.questioner.MigrationQuestioner)  
Added blocks for enum operations.

**InteractiveMigrationQuestioner** (django.db.migrations.questioner.InteractiveMigrationQuestioner)  
Added questions for how to handle changes to enums.

**MigrationAutoDetector** (django.db.migrations.autodetector.MigrationAutoDetector)  
Added method to detect changes in enums and generate operations for them.
Currently hooked into the start of _generate_created_models()_ as enum types must be declared before used in a new model.
 
**BaseDatabaseFeatures** (django.db.backends.base.features.BaseDatabaseFeatures  
Added feature flags for enums.

**BaseDatabaseSchemaEditor** (django.db.backends.base.schema.BaseDatabaseSchemaEditor) 
Modified _\_alter_column_type_sql()_ to support parametised types.

**PostgresDatabaseFeatures** (django.db.backends.postgresl.features.DatabaseFeatures)  
Added feature flags for enums.

**PostgresDatabaseSchemaEditor** (django.db.backends.postgresql.schema.DatabaseSchemaEditor)  
Added sql templates for enum types.

**PostgresDatabaseWrapper** (django.db.backends.postgres.base.DatabaseWrapper)  
Added EnumField data type.

**MysqlDatabaseFeatures** (django.db.backends.mysql.features.DatabaseFeatures)  
Added feature flags for enums.

**MysqlDatabaseWrapper** (django.db.backends.mysql.base.DatabaseWrapper)  
Added EnumField data type.
