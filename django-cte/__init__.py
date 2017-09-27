""" Apply CTE monkey patches to Django

    At present these patches must be updated manually to conform with new CTE
     implementations, but this is only necessary to use new functionality.

    Copy full modified files to here for local import.
    Order of patching *matters*.
"""

from importlib import reload
# Framework imports
import django
# Project imports
from patchy import patchy


def patch_cte():

    with patchy('django-cte') as p:
        p.module('django.db.models.expressions').add('CTERef')

        with p.module('django.db.models.sql.compiler') as m:
            m.cls('SQLCompiler').auto()
            m.cls('SQLUpdateCompiler').auto()
            m.add('SQLInsertReturningCompiler',
                'SQLUpdateReturningCompiler',
                'SQLWithCompiler',
                'SQLLiteralCompiler')
        p.module('django.db.models.sql.subqueries').add(
            '__all__',
            'UpdateReturningQuery',
            'InsertReturningQuery',
            'WithQuery',
            'LiteralQuery')
        # Force reload so that new query types are correctly seen
        reload(django.db.models.sql)

        with p.module('django.db.models.query') as m:
            m.add('LiteralQuerySet')
            m.cls('QuerySet').auto()

        p.module('django.db.models.manager').cls('BaseManager').auto()
        p.module('django.db.models.base').cls('Model').add('as_literal')
