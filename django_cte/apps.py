from django.apps import AppConfig
from . import patch_cte

class DjangoCTEConfig(AppConfig):
    name = 'django_cte'

    def ready(self):
        patch_cte()
