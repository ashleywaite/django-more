# django_enum

Provides a cross-database implementation of an EnumField for Django 1.11+.  
It uses [_django_types_](../django_types/) to provide mechanisms for state tracking in migration that need to be updated and modified at different stages, so that versioning is consistent in older states - enforcing correct enum states at the time of that migration instead of the current state of the enum in the project code.


## EnumField

The EnumField takes an Enum as its argument, and the field created can be set by value (string) corresponding with the values specified in the Enum, or using the Enum members themselves.

Sample:
```python
from django.db import models
from enum import Enum
from django_enum import EnumField, enum_meta

class DaysEnum(Enum):
  MON = 'Monday'
  TUE = 'Tuesday'
  WED = 'Wednesday'

  @enum_meta
  class Meta:
      db_type = 'my_type'
      app_label = 'my_app'

class MyModel(models.Model):
  day = EnumField(DaysEnum)


instance = MyModel(day=DaysEnum.MON)
MyModel.objects.filter(day='Monday')

```

Where the database supports enum types they will be used, by declaring types and modifying them (postgres), modifying the field types inline (mysql) or defaulting to a character field if there's no database support.

**enum_meta** decorator is used to hide the _Meta_ class from being included as a member of the Enum.

**Meta class** If provided allows you to specify the app_label and/or the name of the database type you wish to use instead of having them be automatically generated.


## Django patches

Changes to Django that are necessary are applied by _patch_enum()_ using [_patchy_](../patchy/).
These are automatically applied via the app [_ready()_](apps.py) if you place django_enum into installed apps.

**MigrationQuestioner** (django.db.migrations.questioner.MigrationQuestioner)  
Added blocks for enum operations.

**InteractiveMigrationQuestioner** (django.db.migrations.questioner.InteractiveMigrationQuestioner)  
Added questions for how to handle changes to enums.

**MigrationAutoDetector** (django.db.migrations.autodetector.MigrationAutoDetector)  
Added method to detect changes in enums and generate operations for them.
Currently hooked into the start of _generate_created_models()_ as enum types must be declared before used in a new model.

**BaseDatabaseFeatures** (django.db.backends.base.features.BaseDatabaseFeatures  
Added feature flags for enums.

**PostgresDatabaseFeatures** (django.db.backends.postgresl.features.DatabaseFeatures)  
Added feature flags for enums.

**PostgresDatabaseSchemaEditor** (django.db.backends.postgresql.schema.DatabaseSchemaEditor)  
Added sql templates for enum types.

**MysqlDatabaseFeatures** (django.db.backends.mysql.features.DatabaseFeatures)  
Added feature flags for enums.
