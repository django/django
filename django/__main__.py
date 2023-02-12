"""
Invokes django-admin when the django module is run as a script.

Example: python -m django check
"""
from django.core import management

if __name__ == "__main__":
    
    management.execute_from_command_line()
