from setuptools import setup

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
        'django_enum'
    ],
    install_requires=[
        'django'
    ]
)
