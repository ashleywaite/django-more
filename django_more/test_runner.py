from importlib.util import find_spec
import unittest

from django.apps import apps
from django.conf import settings
from django.test.runner import DiscoverRunner

__all__ = [
    'RunnerWithTestModels',
    ]


class TestLoader(unittest.TestLoader):
    """ Loader that reports all successful loads to a runner """
    def __init__(self, *args, runner, **kwargs):
        self.runner = runner
        super().__init__(*args, **kwargs)

    def loadTestsFromModule(self, module, pattern=None):
        suite = super().loadTestsFromModule(module, pattern)
        if suite.countTestCases():
            self.runner.register_test_module(module)
        return suite


class RunnerWithTestModels(DiscoverRunner):
    """ Test Runner that will add any test packages with a 'models' module to INSTALLED_APPS.
        Allows test only models to be defined within any package that contains tests.
        All test models should be set with app_label = 'tests'
    """
    def __init__(self, *args, **kwargs):
        self.test_packages = set()
        self.test_loader = TestLoader(runner=self)
        super().__init__(*args, **kwargs)

    def register_test_module(self, module):
        self.test_packages.add(module.__package__)

    def setup_databases(self, **kwargs):
        # Look for test models
        test_apps = set()
        for package in self.test_packages:
            if find_spec('.models', package):
                test_apps.add(package)
        # Add test apps with models to INSTALLED_APPS that aren't already there
        new_installed = settings.INSTALLED_APPS + tuple(ta for ta in test_apps if ta not in settings.INSTALLED_APPS)
        apps.set_installed_apps(new_installed)
        return super().setup_databases(**kwargs)
