from django.apps import AppConfig


class DjangoMoreAppConfig(AppConfig):
    name = 'django_more'

    def ready(self):
        # If no support for add_type, apply django_types to add it
        from django.db.migrations.state import ProjectState
        if not hasattr(ProjectState, 'add_type'):
            from django_types import patch_types
            patch_types()
