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
        'django-more',
        'django-more.storages',
        'django-cte',
        'django-enum'
    ],
    install_requires=[
        'django'
    ]
)
