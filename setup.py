from setuptools import setup

setup(
    name="django-more",
    version="0.1",
    description="Django with more",
    long_description=open("README.md").read(),
    packages=[
        "django-cte"
    ],
    install_requires=[
        "django"
    ]
)
