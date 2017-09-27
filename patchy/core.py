""" Generic monkey patching functions for doing it (mostly) safely """

import inspect
import logging
from types import MethodType
from importlib import import_module, reload
from importlib.util import find_spec
from contextlib import suppress, contextmanager

__all__ = ['patchy']

logger = logging.getLogger(__name__)


@contextmanager
def patchy(patch_root=None, module_sep=None):
    yield PatchBase(patch_root, module_sep)


def shadow():
    frame = inspect.currentframe()
    f_back = frame.f_back
    try:
        # do something with the frame
    finally:
        del frame
        del f_back


class PatchBase:
    patch_root = None
    module_sep = '_'

    def __init__(self, patch_root=None, module_sep=None):
        if patch_root is not None:
            try:
                import_module(patch_root)
                self.patch_root = patch_root
            except ImportError:
                raise ValueError("No module found at specified patch_root")
        if module_sep is not None:
            self.module_sep = module_sep

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def module(self, module, source_module=None):
        return PatchModule(self, module, source_module)


class PatchModule(PatchBase):

    def __init__(self, patcher, module, source_module=None):
        self.from_patcher(patcher)
        self.module = import_module(module)
        if source_module:
            self.source_module = source_module

    def from_patcher(self, patcher):
        self.patch_root = patcher.patch_root
        self.module_sep = patcher.module_sep

    def cls(self, cls, source_cls=None):
        return PatchClass(self, cls, source_cls=source_cls)

    @property
    def source_module(self):
        with suppress(AttributeError):
            return self._source_module

        self.source_module = self.module.__name__
        return self._source_module

    @source_module.setter
    def source_module(self, source):
        if inspect.ismodule(source):
            self._source_module = source
        elif isinstance(source, str):
            if self.module_sep is not None:
                source = source.replace('.', self.module_sep)
            if self.patch_root is not None:
                self._source_module = import_module('.' + source, package=self.patch_root)
            else:
                self._source_module = import_module(source)
        else:
            raise TypeError("Must be a valid module or module name")

    def add(self, *attrs, **kattrs):
        """ Add attributes or classes """
        if kattrs:
            logger.info("Patching {m} directly with attrs: {a}".format(
                m=self.module.__name__,
                a=kattrs.keys()))
            for attr, value in kattrs:
                setattr(self.module, attr, value)
        if attrs:
            logger.info("Patching {m} from {pm} with attrs: {a}".format(
                m=self.module.__name__,
                pm=self.source_module.__name__,
                a=attrs))
            for attr in attrs:
                # Treat objects as assigned by their name
                if hasattr(attr, "__name__"):
                    (attr, value) = (attr.__name__, attr)
                else:
                    value = getattr(self.module, attr)
                setattr(self.module, attr, value)

    def auto(self, predicate=inspect.isclass):
        self._auto(self.source_module, predicate)

    def _auto(self, source, predicate):
        attrs = [o[0] for o in inspect.getmembers(source, predicate)]
        self.add(*attrs)


class PatchClass(PatchModule):

    def __init__(self, module, cls, source_cls=None):
        self.from_module(module)
        self.cls = getattr(self.module, cls)
        if source_cls:
            self.source_cls = source_cls

    def from_module(self, module):
        self.from_patcher(module)
        with suppress(AttributeError):
            self._source_module = module._source_module
        self.module = module.module

    @property
    def source_cls(self):
        with suppress(AttributeError):
            return self._source_cls

        self.source_cls = self.cls.__name__
        return self._source_cls

    @source_cls.setter
    def source_cls(self, source):
        if inspect.isclass(source):
            self._source_cls = source
        elif isinstance(source, str):
            self._source_cls = getattr(self.source_module, source)
        else:
            raise TypeError("Must be a valid class or class name")

    def auto(self, predicate=inspect.isfunction):
        self._auto(self.source_cls, predicate)

    def add(self, *attrs, **kattrs):
        """ Add attributes or classes """
        if kattrs:
            logger.info("Patching {m}.{c} directly with attrs: {a}".format(
                m=self.module.__name__,
                c=self.cls.__name__,
                a=kattrs.keys()))
            for attr, value in kattrs:
                setattr(self.cls, attr, value)
        for attr in attrs:
            # Treat objects as assigned by their name
            if hasattr(attr, "__name__"):
                (attr, value) = (attr.__name__, attr)
            else:
                value = getattr(self.source_cls, attr)
            logger.debug(" {c}.{a} was {f1}, but will be {f2}{r}".format(
                c=self.cls.__name__,
                a=attr,
                f1=getattr(self.cls, attr) if hasattr(self.cls, attr) else "none",
                f2=value,
                r=" which will be rebound" if isinstance(value, MethodType) else ""))
            if isinstance(value, MethodType):
                setattr(self.cls, attr, classmethod(value.__func__))
            else:
                setattr(self.cls, attr, value)
