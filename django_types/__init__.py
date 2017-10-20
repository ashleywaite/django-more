
import logging
# Project imports
from patchy import patchy
from .fields import *
from .operations import *


logger = logging.getLogger(__name__)


def patch_types():
    """ Applies the patches necessary for django_types to work """
    logger.info('Applying django_types patches')

    # Patch migration classes to statefully apply types
    with patchy('django.db', 'django_types.patches') as p:
        p.cls('migrations.state.ProjectState').auto(allow={'apps'})
        p.cls('migrations.state.StateApps').auto()

        # Patch backend classes to allow parametised db_types
        p.cls('backends.base.schema.BaseDatabaseSchemaEditor').auto(allow={'_alter_column_type_sql'})
