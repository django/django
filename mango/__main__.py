"""
Invokes mango-admin when the mango module is run as a script.

Example: python -m mango check
"""
from mango.core import management

if __name__ == "__main__":
    management.execute_from_command_line()
