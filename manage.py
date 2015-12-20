#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    sys.path.append('src')
    settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
    assert settings_module, "DJANGO_SETTINGS_MODULE env var is required"

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
