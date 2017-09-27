""" Apply CTE monkey patches to Django

    At present these patches must be updated manually to conform with new CTE
     implementations, but this is only necessary to use new functionality.

    To get listing of changes (compared to Django 2.x dev) use this:
     https://github.com/django/django/compare/master...ashleywaite:cte-dev#files_bucket

    Copy full modified files to here for local import.
    Order of patching *matters*.
"""

import inspect
import logging
from types import MethodType
from importlib import import_module, reload
# Framework imports
import django
from django.utils.termcolors import colorize

logger = logging.getLogger(__name__)


def module_patch(mod, attrs=None, patch_ref="sidutils.django.patched"):
    import_module(patch_ref)
    module = import_module(mod)
    patch_mod = import_module('.' + mod.replace('.', '_'), package=patch_ref)
    if not attrs:
        attrs = [o[0] for o in inspect.getmembers(patch_mod, inspect.isclass)]
    logger.info("Patching {m} with attrs: {a}".format(
        m=colorize(mod, fg="blue"),
        a=colorize(attrs, fg="green")))
    for attr in attrs:
        patch_attr = getattr(patch_mod, attr)
        setattr(module, attr, patch_attr)


def class_patch(mod, cls, attrs=None, patch_ref="sidutils.django.patched"):
    import_module(patch_ref)
    module = import_module(mod)
    obj = getattr(module, cls)
    patch_module = import_module('.' + mod.replace('.', '_'), package=patch_ref)
    patch_obj = getattr(patch_module, cls)
    if not attrs:
        attrs = [o[0] for o in inspect.getmembers(patch_obj, inspect.isfunction)]
    logger.info("Patching {m}.{c} with attrs: {a}".format(
        m=colorize(mod, fg="blue"),
        c=colorize(cls, fg="cyan"),
        a=colorize(attrs, fg="green")))
    for attr in attrs:
        patch_attr = getattr(patch_obj, attr)
        logger.debug(" attr {o}.{a} was {f1}, but will be {f2}{r}".format(
            o=colorize(obj.__name__, fg="cyan"),
            a=colorize(attr, fg="green"),
            f1=getattr(obj, attr) if hasattr(obj, attr) else "none",
            f2=colorize(patch_attr, fg="red"),
            r=" which will be rebound" if isinstance(patch_attr, MethodType) else ""
        ))
        if isinstance(patch_attr, MethodType):
            setattr(obj, attr, classmethod(patch_attr.__func__))
        else:
            setattr(obj, attr, patch_attr)


def patch_django():
    # Patch django/db/models/expressions.py
    module_patch("django.db.models.expressions", attrs=["CTERef"])

    # Patch django/db/models/sql/compiler.py
    class_patch("django.db.models.sql.compiler", "SQLCompiler")
    class_patch("django.db.models.sql.compiler", "SQLUpdateCompiler")
    module_patch("django.db.models.sql.compiler", attrs=[
        "SQLInsertReturningCompiler",
        "SQLUpdateReturningCompiler",
        "SQLWithCompiler",
        "SQLLiteralCompiler"])

    # Patch django/db/models/sql/subqueries.py
    module_patch("django.db.models.sql.subqueries", attrs=[
        "__all__",
        "UpdateReturningQuery",
        "InsertReturningQuery",
        "WithQuery",
        "LiteralQuery"])
    reload(django.db.models.sql)

    # Patch django/db/models/query.py
    module_patch("django.db.models.query", attrs=["LiteralQuerySet"])
    class_patch("django.db.models.query", "QuerySet")

    # Patch django/db/models/manager.py
    class_patch("django.db.models.manager", "BaseManager")

    # Patch django/db/models/base.py
    class_patch("django.db.models.base", "Model", attrs=["as_literal"])
