"""
Invokes thibaud-admin when the thibaud module is run as a script.

Example: python -m thibaud check
"""

from thibaud.core import management

if __name__ == "__main__":
    management.execute_from_command_line()
