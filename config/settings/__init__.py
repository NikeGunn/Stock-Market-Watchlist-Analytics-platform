"""
Settings module initialization.

Automatically imports the correct settings based on DJANGO_ENV environment variable.
"""

import os
from decouple import config

# Determine which settings to use
ENVIRONMENT = config('DJANGO_ENV', default='development')

if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'staging':
    from .staging import *
else:
    from .development import *
