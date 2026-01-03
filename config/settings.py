"""
DEPRECATED: This file is kept for backward compatibility.

New settings structure:
- config/settings/base.py - Base settings
- config/settings/development.py - Development settings
- config/settings/staging.py - Staging settings
- config/settings/production.py - Production settings

The correct settings are imported based on DJANGO_ENV environment variable.
"""

# Import from new settings structure
from config.settings import *

import warnings
warnings.warn(
    "config.settings is deprecated. Use environment-based settings via DJANGO_ENV variable.",
    DeprecationWarning,
    stacklevel=2
)
