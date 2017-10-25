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

### Field options

**choices** follows the typical convention of (value, display) tuples, where the value can be the enum member or text value of it. Using this syntax grouped choices can be displayed.  
_eg. No Wednesday choice, choices=[(DaysEnum.MON, 'Monday'), (DaysEnum.TUE, 'Tuesday')]_

It also allows for enum members to be used at the top level of the list, which will be automatically replaced with (enum_member, enum_value) for convenience.  
_eg. No Wednesday choice, choices=[DaysEnum.MON, DaysEnum.TUE]_

**on_delete** defines the behaviour for when an enum value is removed from the definition, and follows the same conventions as the foreign key on_delete.  
_eg. Prevent migration if any records have removed value, on_delete=models.PROTECT_

This behaviour can be overridden when making a migration, as it will confirm the behaviour to apply.

### Enum class options

**enum_meta** decorator is used to hide the _Meta_ class from being included as a member of the Enum.

**Meta class** if provided allows you to specify the app_label and/or the name of the database type you wish to use instead of having them be automatically generated.


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
