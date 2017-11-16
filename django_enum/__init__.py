
import logging
# Framework imports
from django.conf import settings
# Project imports
from patchy import patchy
from .fields import *


logger = logging.getLogger(__name__)
default_app_config = 'django_enum.apps.DjangoEnumConfig'


def patch_enum():
    """ Applies the patches necessary for django_enum to work """
    # Patch migrations classes
    logger.info('Applying django_enum patches')

    # If no support for add_type, apply django_types to add it
    from django.db.migrations.state import ProjectState
    if not hasattr(ProjectState, 'add_type'):
        from django_types import patch_types
        patch_types()

    with patchy('django.db.migrations', 'django_enum.patches') as p:
        p.cls('questioner.MigrationQuestioner').auto()
        p.cls('questioner.InteractiveMigrationQuestioner').auto()
        p.cls('autodetector.MigrationAutodetector').auto()

    # Patch backend features
    with patchy('django.db.backends', 'django_enum.patches') as p:
        # Add base changes necessary
        p.cls('base.features.BaseDatabaseFeatures').auto()

        # Only patch database backends in use (avoid dependencies)
        for backend in set(db_dict['ENGINE'] for db_name, db_dict in settings.DATABASES.items()):
            if backend == 'django.db.backends.postgresql':
                import django.db.backends.postgresql.base
                p.cls('postgresql.features.DatabaseFeatures', 'PostgresDatabaseFeatures').auto()
                p.cls('postgresql.schema.DatabaseSchemaEditor', 'PostgresDatabaseSchemaEditor').auto()
            if backend == 'django.db.backends.mysql':
                import django.db.backends.mysql.base
                p.cls('mysql.features.DatabaseFeatures', 'MysqlDatabaseFeatures').auto()
