""" Apply CTE monkey patches to Django

    At present these patches must be updated manually to conform with new CTE
     implementations, but this is only necessary to use new functionality.

    Order of patching *matters*.
"""
from importlib import reload, import_module
# Project imports
from patchy import patchy


def patch_cte():
    with patchy('django.db.models', 'django_cte') as p:
        p.mod('expressions').add('CTERef')

        with p.mod('sql.compiler') as m:
            m.cls('SQLCompiler').auto()
            m.cls('SQLUpdateCompiler').auto()
            m.add('SQLInsertReturningCompiler',
                'SQLUpdateReturningCompiler',
                'SQLWithCompiler',
                'SQLLiteralCompiler')
        with p.mod('sql.subqueries') as m:
            m.merge(
                '__all__',
                'UpdateReturningQuery',
                'InsertReturningQuery',
                'WithQuery',
                'LiteralQuery')
        # Force reload so that new query types are correctly seen
        reload(import_module('django.db.models.sql'))

        with p.mod('query') as m:
            m.add('LiteralQuerySet')
            m.cls('QuerySet').auto()

        p.cls('manager.BaseManager').auto()
        p.cls('base.Model').add('as_literal')
