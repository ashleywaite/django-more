""" Generic monkey patching functions for doing it (mostly) safely """

import logging
import inspect
from types import MethodType, ModuleType
from collections import abc
from importlib import import_module
from importlib.util import resolve_name
from contextlib import suppress

__all__ = ['patchy', 'super_patchy']

logger = logging.getLogger(__name__)


class ResolveError(Exception):
    """ Used to indicate terminal exception during resolve """
    pass


class NotFoundError(ResolveError, ImportError):
    pass


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


def super_patchy(*args, do_call=True, **kwargs):
    """ super() for patches!
        When called from within a patched in function will return or call the
        function that it replaced, preserving self/cls arguments
    """
    caller_frame = inspect.currentframe().f_back
    caller = inspect.getargvalues(caller_frame)

    old_func = patchy_records[caller_frame.f_code]

    if caller.args[0] in ['self', 'cls']:
        # If caller has the appearance of being bound (to instance or class)
        old_func = MethodType(old_func, caller.locals[caller.args[0]])
    if do_call:
        return old_func(*args, **kwargs)
    return old_func


def resolve_exposing(name):
    """ Attempt an import but reraise any error other than module not found as terminal to resolving """
    try:
        return import_module(name)
    except ImportError as err:
        # Pass any non-suspicious errors on
        if err.msg.endswith('is not a package') or err.msg.startswith('No module') and name in err.msg:
            raise
        # Reraise any suspicious errors as terminal - resolve fails
        raise ResolveError('Error importing module {n}'.format(n=name)) from err


def resolve(name, package=None):
    """ Turn a dotted name into a module or class reference """
    if isinstance(package, str):
        package = resolve_exposing(package)

    if package:
        name = resolve_name('.{}'.format(name), package.__name__)

    try:
        # Try to get a module
        return resolve_exposing(name)
    except ImportError as err:
        if '.' not in name:
            raise NotFoundError('{n} is not a valid module name'.format(n=name)) from err

    try:
        # Try to get an attribute of a module
        mod, attr = name.rsplit('.', maxsplit=1)
        package = resolve_exposing(mod)
        cls = getattr(package, attr)
        assert(isinstance(cls, type))
        return cls
    except ImportError as err:
        raise NotFoundError('{n} is not a valid class or module name'.format(n=name)) from err
    except AttributeError as err:
        raise NotFoundError('{a} does not exist within {m}'.format(a=attr, m=mod)) from err
    except AssertionError as err:
        raise ResolveError('{a} in {m} is not a valid class'.format(a=attr, m=mod)) from err


class PatchyRecords(dict):
    def __getitem__(self, key):
        with suppress(AttributeError):
            key = key.__code__
        with suppress(KeyError):
            return super().__getitem__(id(key))
        raise RuntimeError('Patched func cannot find its predecessor')

    def __setitem__(self, key, value):
        # Strip inbult decorators
        if isinstance(value, (classmethod, staticmethod)):
            value = value.__func__
        with suppress(AttributeError):
            key = key.__code__
        return super().__setitem__(id(key), value)

    def __delitem__(self, key):
        with suppress(AttributeError):
            key = key.__code__
        return super().__delitem__(id(key))

    def __contains__(self, key):
        with suppress(AttributeError):
            key = key.__code__
        return super().__contains__(id(key))


patchy_records = PatchyRecords()


class PatchBase:
    allow = set()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def auto(self, source=None, *, allow=None, only_allow=None, merge=True):
        """ Apply all attributes of from source to target.
            Defaults to merging collections.
        """
        if only_allow:
            self.allow = only_allow
        elif allow:
            self.allow = self.allow | allow
        attrs = self.get_auto_attrs(source or self.source)
        self.apply(dict(attrs), merge=merge)

    def add(self, *attrs, **kattrs):
        self.apply(attrs, kattrs)

    def merge(self, *attrs, **kattrs):
        self.apply(attrs, kattrs, merge=True)

    def apply(self, attrs=None, kattrs=None, merge=False):
        """ Apply new attributes or classes to the target """
        for attr in attrs:
            kattrs = kattrs or {}
            # Treat objects as assigned to their name
            if hasattr(attr, "__name__"):
                kattrs[attr.__name__] = attr
            else:
                kattrs[attr] = inspect.getattr_static(self.source, attr)
        for attr, value in kattrs.items():
            old_value = inspect.getattr_static(self.target, attr, None)
            # If callable, preserve old func
            if callable(value) and callable(old_value):
                # Prevent duplicate patching
                if value in patchy_records:
                    continue
                patchy_records[value] = old_value

            # Merge collections and classes instead of replacing
            if merge:
                if isinstance(old_value, abc.Container):
                    if isinstance(value, abc.Mapping) and isinstance(old_value, abc.MutableMapping):
                        old_value.update(value)
                        logger.info('Merging mapping {mod}.{attr}'.format(mod=self.target.__name__, attr=attr))
                    elif isinstance(value, abc.Sequence) and isinstance(old_value, abc.MutableSequence):
                        old_value.extend(value)
                        logger.info('Merging sequence {mod}.{attr}'.format(mod=self.target.__name__, attr=attr))
                    elif isinstance(value, abc.Set) and isinstance(old_value, abc.MutableSet):
                        old_value.update(value)
                        logger.info('Merging set {mod}.{attr}'.format(mod=self.target.__name__, attr=attr))
                    else:
                        setattr(self.target, attr, value)
                        logger.info("Couldn't merge collection {target}.{attr}, replaced instead".format(
                            target=self.target.__name__,
                            attr=attr))
                    continue
                elif isinstance(old_value, type):
                    logger.info('Merging class for {target}.{attr}'.format(
                        target=self.target.__name__, attr=attr))
                    self.cls(old_value, value).auto()
                    continue
            logger.info('Setting value {target}.{attr}'.format(target=self.target.__name__, attr=attr))
            # Apply patched value
            setattr(self.target, attr, value)

    def get_attrs(self, source=None, exclude_hidden=True):
        # Get all attributes, except hidden if exclude_hidden
        # but allowing whitelisted attributes (like __all__)
        source = source or self.source
        return (
            (attr, val)
            for attr, val in source.__dict__.items()
            if attr in self.allow
            or not exclude_hidden
            or not attr.startswith('_'))


class PatchModule(PatchBase):
    allow = {'__all__'}

    def __init__(self, target, source=None, module_sep='_'):
        self.target = target
        self.source = source
        self.module_sep = module_sep

    def cls(self, target, source=None):
        if isinstance(target, str):
            target = resolve(target, package=self.target)
        if self.source and source is None:
            with suppress(ImportError):
                source_str = '{mod}.{cls}'.format(
                    mod=target.__module__.replace('.', self.module_sep),
                    cls=target.__name__)
                source = resolve(source_str, package=self.source)
            if not source:
                with suppress(AttributeError):
                    source = getattr(self.source, target.__name__)
        elif isinstance(source, str):
            source = resolve(source, package=self.source)
        if isinstance(target, type):
            return PatchClass(target, source)
        raise TypeError('Must be a valid class or class name')

    def mod(self, target, source=None):
        if isinstance(target, str):
            target = resolve(target, package=self.target.__name__)
        if isinstance(source, str):
            source = resolve(source, package=self.source.__name__)

        elif source is None:
            # Deal with nested modules in a pack
            # Test for corresponding module relative to current source
            source_name = target.__name__.replace('.', self.module_sep)
            with suppress(ImportError):
                source = resolve(source_name, package=self.source.__name__)

        if isinstance(target, ModuleType):
            if source:
                logger.info('Patching {} using {}'.format(target.__name__, source.__name__))
            return PatchModule(target, source, self.module_sep)

    def get_auto_attrs(self, source=None, exclude_hidden=True):
        # Only auto locally declared objects, or attributes in allow
        return (
            (attr, val)
            for attr, val in self.get_attrs(source, exclude_hidden)
            if (hasattr(val, '__module__') and val.__module__ == source.__name__)
            or attr in self.allow)


class PatchClass(PatchBase):
    allow = {'__init__', '__new__'}

    def __init__(self, target, source):
        self.target = target
        self.source = source

    def mod(self):
        return self.target.__module__

    def get_auto_attrs(self, source=None, exclude_hidden=True):
        # Only auto attributes, locally declared objects, or hiddens in allow
        return (
            (attr, val)
            for attr, val in self.get_attrs(source, exclude_hidden)
            if not hasattr(val, '__module__')
            or val.__module__ == source.__module__
            or attr in self.allow)
