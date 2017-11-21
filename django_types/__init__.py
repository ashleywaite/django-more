
import logging
# Project imports
from patchy import patchy
from .fields import CustomTypeField


logger = logging.getLogger(__name__)


def patch_types():
    """ Applies the patches necessary for django_types to work """
    logger.info('Applying django_types patches')

    # Patch fields to provide default dependency information
    with patchy('django.db.models', 'django_types.patches') as p:
        p.cls('Field').auto(allow={'dependencies'})
        p.cls('fields.related.RelatedField').auto()

    # Patch migration classes to statefully apply types and dependencies
    with patchy('django.db.migrations', 'django_types.patches') as p:
        p.cls('autodetector.MigrationAutodetector').auto(allow={
            '_generate_added_field',
            '_generate_altered_foo_together'})
        p.cls('state.ProjectState').auto(allow={'apps'})
        p.cls('state.StateApps').auto()

    # Patch backend classes to allow parametised db_types
    with patchy('django.db.backends', 'django_types.patches') as p:
        p.cls('base.schema.BaseDatabaseSchemaEditor').auto(allow={'_alter_column_type_sql'})
