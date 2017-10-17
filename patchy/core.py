""" Generic monkey patching functions for doing it (mostly) safely """

import logging
import inspect
from types import MethodType, ModuleType, FunctionType
from importlib import import_module
from importlib.util import find_spec
from contextlib import suppress

__all__ = ['patchy', 'super_patchy']

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
    if '.' in path:
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
        for attr in attrs:
            kattrs[attr] = getattr(self.source, attr)
        for attr, value in kattrs.items():
            if isinstance(value, dict):
                getattr(self.target, attr).update(value)
            if isinstance(value, list):
                getattr(self.target, attr).extend(value)

    def auto(self, source=None, *, types=object):
        attrs = get_attrs(source or self.source, types)
        self.add(*attrs)

    def add(self, *attrs, **kattrs):
        """ Add attributes or classes """
        if kattrs:
            for attr, value in kattrs.items():
                apply_patch(self.target, attr, value)
        for attr in attrs:
            # Treat objects as assigned to their name
            if hasattr(attr, "__name__"):
                (attr, value) = (attr.__name__, attr)
            else:
                value = getattr(self.source, attr)
            apply_patch(self.target, attr, value)


class PatchModule(PatchBase):
    def __init__(self, target, source=None, module_sep='_'):
        self.target = target
        self.source = source
        self.module_sep = module_sep

    def cls(self, target, source=None):
        if isinstance(target, str):
            if '.'  in target:
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


def super_patchy(*args, do_call=True, **kwargs):
    caller_frame = inspect.currentframe().f_back
    caller = inspect.getargvalues(caller_frame)

    old_func = get_records(caller_frame).get(id(caller_frame.f_code))

    if not old_func:
        raise RuntimeError('Patched func cannot find its predecessor')

    if caller.args[0] in ['self', 'cls']:
        # If caller has the appearance of being bound (to instance or class)
        old_func = MethodType(old_func, caller.locals[caller.args[0]])
    if do_call:
        return old_func(*args, **kwargs)
    return old_func


def get_records(context, patchy_var='__patchy__'):
    with suppress(AttributeError):
        # From a frame
        return context.f_globals[patchy_var]
    # Ensure patchy records exist
    if patchy_var not in context.__globals__:
        context.__globals__[patchy_var] = {}
    return context.__globals__.get(patchy_var)


def apply_patch(target, attr, value):
    old_value = inspect.getattr_static(target, attr, None)

    # If callable, preserve old func
    if callable(value) and callable(old_value):
        patchy_records = get_records(value)
        # Prevent duplicate patching
        if id(value.__code__) in patchy_records:
            return
        # Strip inbult decorators
        if isinstance(old_value, (classmethod, staticmethod)):
            old_value = old_value.__func__

        patchy_records[id(value.__code__)] = old_value

    # Apply patched value
    setattr(target, attr, value)


class PatchClass(PatchBase):
    def __init__(self, target, source):
        self.target = target
        self.source = source

    def mod(self):
        return self.target.__module__

    # Replacing
    def add_desc(self, *attrs, **kattrs):
        for attr, value in kattrs.items():
            setattr(self.target, attr, value)
        for attr in attrs:
            # Treat objects as assigned to their name
            if hasattr(attr, "__name__"):
                (attr, value) = (attr.__name__, attr)
            else:
                value = self.source.__dict__[attr]
            old_val = self.target.__dict__.get(attr, None)
            setattr(self.target, attr, value)
