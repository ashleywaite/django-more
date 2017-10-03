""" Generic monkey patching functions for doing it (mostly) safely """

import logging
from types import MethodType, ModuleType, FunctionType
from importlib import import_module
from importlib.util import find_spec
from contextlib import suppress

__all__ = ['patchy']

logger = logging.getLogger(__name__)


def patchy(target, source=None):
    """ If source is not supplied, auto updates cannot be applied """
    if isinstance(target, str):
        target = resolve(target)
    if isinstance(source, str):
        source = resolve(source)
    if isinstance(target, ModuleType):
        return PatchModule(target, source)
    elif isinstance(target, type) and source:
        return PatchClass(target, source)


def resolve(path):
    """ Turn a dotted name into a module or class reference """
    with suppress(AttributeError, ModuleNotFoundError):
        find_spec(path)
        return import_module(path)
    if path.find('.'):
        mod_str, cls_str = path.rsplit('.', maxsplit=1)
        mod = import_module(mod_str)
        return getattr(mod, cls_str)
    raise ValueError('Must be a valid class or module name')

# inspect.getmembers includes values in mro
# obj.__dict__ includes hidden attributes
# obj.__dict__ returns wrapped objects
# Use obj.__dict__ with getattr() to avoid mro and wrappings
def get_attrs(obj, types, exclude_hidden=True):
    """ Get the locally declared attributes of an object filtered by type """
    attrs = ((k, getattr(obj, k)) for k in obj.__dict__ if not exclude_hidden or not k.startswith('_'))
    return [k for k, v in attrs if isinstance(v, types)]


class PatchBase:

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def merge(self, *attrs, **kattrs):
        for attr, value in kattrs:
            if isinstance(value, dict):
                getattr(self.target, attr).update(value)

    def _auto(self, source, types):
        attrs = get_attrs(source, types)
        self.add(*attrs)


class PatchModule(PatchBase):
    def __init__(self, target, source=None, module_sep='_'):
        self.target = target
        self.source = source
        self.module_sep = module_sep

    def cls(self, target, source=None):
        if isinstance(target, str):
            if target.find('.'):
                mod_str, target = target.rsplit('.', maxsplit=1)
                mod = import_module('.' + mod_str, package=self.target.__name__)
            else:
                mod = self.target
            target = getattr(mod, target)
        if isinstance(source, str):
            source = getattr(self.source, source)

        if isinstance(target, type):
            return PatchClass(target, source)
        raise TypeError('Must be a valid class or class name')

    def mod(self, target, source=None):
        if isinstance(target, str):
            target = import_module('.' + target, package=self.target.__name__)
        if isinstance(source, str):
            source = import_module('.' + source, package=self.source.__name__)
        elif source is None:
            #parent = import_module('..', package=self.source.__name__)
            # Deal with nested modules in a pack
            source_name = target.__name__.replace('.', self.module_sep)
            source = import_module('..' + source, package=self.source.__name__)

        if isinstance(target, ModuleType):
            return PatchModule(target, source, self.module_sep)

    def add(self, *attrs, **kattrs):
        """ Add attributes or classes """
        if kattrs:
            logger.info("Patching {m} directly with attrs: {a}".format(
                m=self.target.__name__,
                a=kattrs.keys()))
            for attr, value in kattrs:
                setattr(self.target, attr, value)
        if attrs:
            logger.info("Patching {m} from {pm} with attrs: {a}".format(
                m=self.target.__name__,
                pm=self.source.__name__,
                a=attrs))
            for attr in attrs:
                # Treat objects as assigned by their name
                if hasattr(attr, "__name__"):
                    (attr, value) = (attr.__name__, attr)
                else:
                    value = getattr(self.source, attr)
                setattr(self.target, attr, value)

    def auto(self, types=object):
        self._auto(self.source, types)


class PatchClass(PatchBase):
    def __init__(self, target, source):
        self.target = target
        self.source = source

    def mod(self):
        return self.target.__module__

    def auto(self, types=object):
        self._auto(self.source, types)

    def add(self, *attrs, **kattrs):
        """ Add attributes or classes """
        if kattrs:
            logger.info("Patching {m}.{c} directly with attrs: {a}".format(
                m=self.target.__module__,
                c=self.target.__name__,
                a=kattrs.keys()))
            for attr, value in kattrs:
                setattr(self.target, attr, value)
        for attr in attrs:
            # Treat objects as assigned to their name
            if hasattr(attr, "__name__"):
                (attr, value) = (attr.__name__, attr)
            else:
                value = getattr(self.source, attr)
            old_val = getattr(self.target, attr, None)
            logger.debug(" {c}.{a} was {f1}, but will be {f2}{r}".format(
                c=self.target.__name__,
                a=attr,
                f1=old_val,
                f2=value,
                r=" as a classmethod" if isinstance(value, MethodType) else ""))
            if isinstance(value, MethodType):
                # Rebind if a classmethod and make old value available
                setattr(value.__func__, '__patched__', old_val)
                setattr(self.target, attr, classmethod(value.__func__))
            elif isinstance(value, FunctionType):
                # Make old value available, but will not be bound to instances if a function
                setattr(value, '__patched__', old_val)
                setattr(self.target, attr, value)
            else:
                setattr(self.target, attr, value)
