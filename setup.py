from setuptools import setup


test_deps = [
    'psycopg2',
    'mysqlclient',
]
extras = {
    'test': test_deps,
}

setup(
    name='django-more',
    version='0.1',
    author='Ashley Waite',
    author_email='ashley.c.waite@gmail.com',
    description='Django with more',
    long_description=open('README.md').read(),
    packages=[
        'patchy',
        'django_more',
        'django_more.storages',
        'django_cte',
        'django_enum',
    ],
    install_requires=[
        'django',
    ],
    test_suite = 'tests.runtests.runtests',
    tests_require=test_deps,
    extras_require=extras,
)
