from setuptools import setup
import pypandoc

test_deps = [
    'psycopg2',
    'mysqlclient',
]
extras = {
    'test': test_deps,
}

setup(
    name='django-more',
    version='0.2.3',
    author='Ashley Waite',
    author_email='ashley.c.waite@gmail.com',
    description='Django with more',
    long_description=pypandoc.convert('README.md', 'rst'),
    url='https://github.com/ashleywaite/django-more',
    packages=[
        'patchy',
        'django_more',
        'django_more.fields',
        'django_more.storages',
        'django_enum',
        'django_types',
    ],
    install_requires=[
        'django',
    ],
    python_requires='>=3.4',
    test_suite='tests.runtests.runtests',
    tests_require=test_deps,
    extras_require=extras,
    license='BSD',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Django :: 1.11',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
