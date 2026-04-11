import os
import sys

# Add current directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'creativesphere.settings')

import django
django.setup()

from django.core.management import execute_from_command_line

if __name__ == '__main__':
 execute_from_command_line(['manage.py', 'runserver', '8000'])
