import os

SECRET_KEY = 'justtesting'

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.auth',
    'django.contrib.admin',
    'django_enum',
    'django_cte',
    'tests',
)

DEBUG = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASE_ENGINES = {
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test_django_more.sqlite3',
    },
    'postgresql': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_django_more',
        'TEST': {'NAME': 'test_django_more'},
        'USER': os.getenv('TEST_DB_NAME', 'testuser'),
        'PASSWORD': os.getenv('TEST_DB_PASS', 'testpass'),
        'HOST': 'localhost',
        'PORT': 5432,
    },
    'mysql': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'test_django_more',
        'TEST': {'NAME': 'test_django_more'},
        'USER': os.getenv('TEST_DB_NAME', 'testuser'),
        'PASSWORD': os.getenv('TEST_DB_PASS', 'testpass'),
        'HOST': 'localhost',
    },
}

# Use database dependant on ENV
DATABASES = {
    'default': DATABASE_ENGINES[os.getenv('USING_DB_ALIAS')]
}

LOGGING = {
    'version': 1,
    'formatters': {
        'simple': {
            'format': '[%(asctime)s] %(levelname)s %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'patchy': {
            'handlers': ['console'],
            'level': 'WARN',
        },
    },
}
