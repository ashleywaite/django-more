""" Import sugar for django """
# System imports
import sys
from functools import lru_cache
from contextlib import suppress
# Framework imports
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import get_storage_class


# Lazy import wrapper so named storages can be referenced as
#  django-more.storages.NAME
class Storages:
    def __getattribute__(self, attr):
        return make_storage(attr)


# Create and cache storage classes on demand
@lru_cache(maxsize=16)
def make_storage(storage_name):
    conf = settings.STORAGES.get(storage_name)
    with suppress(ImportError, KeyError):
        klass = get_storage_class(conf.pop("class"))
        return type(storage_name, (klass, ), conf)
    raise ImproperlyConfigured("Storage '{sn}' is not correctly declared".format(sn=storage_name))


sys.modules[__name__] = Storages()
