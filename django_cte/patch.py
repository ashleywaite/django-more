""" Apply CTE monkey patches to Django

    At present these patches must be updated manually to conform with new CTE
     implementations, but this is only necessary to use new functionality.

    Order of patching *matters* due to namespace reload.
"""
from importlib import reload, import_module
# Project imports
from patchy import patchy


def patch_cte():
    with patchy('django.db.models', 'django_cte') as p:
        p.mod('expressions').auto()
        p.mod('sql.compiler').auto()
        p.mod('sql.subqueries').auto()
        # Force reload so that new query types are imported into namespace
        reload(import_module('django.db.models.sql'))

        p.mod('query').auto()
        p.cls('manager.BaseManager').auto()
        p.cls('base.Model').auto()
