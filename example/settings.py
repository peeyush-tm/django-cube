# we add django-cube to the path
import sys
import os
sys.path.append(os.path.abspath('..'))

# Django settings for example project.
DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'bookcase.sqlite',                      # Or path to database file if using sqlite3.
    }
}

ROOT_URLCONF = 'example.urls'

INSTALLED_APPS = (
    'example.bookcase',
    'cube',
)
