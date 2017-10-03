from django.apps import AppConfig
from .patch import patch_enum

class DjangoEnumConfig(AppConfig):
    name = 'django-enum'

    def ready(self):
        patch_enum()
