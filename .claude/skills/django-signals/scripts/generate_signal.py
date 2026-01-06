#!/usr/bin/env python
"""
Django Signal Generator

Generates boilerplate code for custom signals and handlers.

Usage:
    python generate_signal.py --app myapp --signal payment_completed --args "payment,amount,transaction_id"
    python generate_signal.py --app myapp --signal order_shipped --args "order,tracking_number,carrier"

Features:
    - Generates signal definition with documentation
    - Creates example sender code
    - Creates example receiver code
    - Generates test template
    - Updates app files (signals.py, handlers.py)
"""

import argparse
import sys
from pathlib import Path
from typing import List


SIGNAL_TEMPLATE = '''"""
{docstring}

Arguments:
{args_doc}

Example:
    from {app}.signals import {signal_name}

    {signal_name}.send(
        sender={sender_class},
{example_args}
    )
"""
'''

SIGNALS_FILE_TEMPLATE = '''"""
Custom signals for {app} app.
"""
from django.dispatch import Signal

# {signal_description}
{signal_name} = Signal()
{signal_name}.__doc__ = """{docstring}

Arguments:
{args_doc}

Example:
    from {app}.signals import {signal_name}

    {signal_name}.send(
        sender={sender_class},
{example_args}
    )
"""
'''

HANDLER_TEMPLATE = '''from django.dispatch import receiver
from {app}.signals import {signal_name}


@receiver({signal_name}, dispatch_uid="{dispatch_uid}")
def handle_{signal_name}(sender, {args}, **kwargs):
    """
    Handle {signal_name} signal.

    Args:
        sender: The sender class
{handler_args_doc}
        **kwargs: Additional arguments
    """
    # TODO: Implement handler logic
    pass
'''

SENDER_EXAMPLE_TEMPLATE = '''# Example: Sending {signal_name} signal

from {app}.signals import {signal_name}
from {app}.models import {sender_class}

def example_function():
    """Example function that sends the signal."""
    # Your business logic here
    {example_instance_creation}

    # Send the signal
    {signal_name}.send(
        sender={sender_class},
{example_args}
    )
'''

TEST_TEMPLATE = '''from django.test import TestCase
from {app}.signals import {signal_name}


class {signal_class}Tests(TestCase):
    """Tests for {signal_name} signal."""

    def test_signal_sent(self):
        """Test that {signal_name} signal is sent correctly."""
        received = []

        def test_receiver(sender, {args}, **kwargs):
            received.append({{
                'sender': sender,
{test_received_dict}
            }})

        # Connect test receiver
        {signal_name}.connect(test_receiver)

        try:
            # TODO: Trigger code that sends the signal
            # Example:
            # from {app}.services import process_{function_name}
            # result = process_{function_name}(...)

            # Verify signal was sent
            self.assertEqual(len(received), 1)
            # self.assertEqual(received[0]['sender'], ExpectedSender)
            # Add more assertions as needed
        finally:
            # Clean up
            {signal_name}.disconnect(test_receiver)

    def test_signal_handler(self):
        """Test that signal handler works correctly."""
        # TODO: Test the actual handler behavior
        # Example:
        # from {app}.handlers import handle_{signal_name}
        # handle_{signal_name}(sender=YourModel, {example_handler_call})
        pass
'''


class SignalGenerator:
    """Generator for Django signals boilerplate."""

    def __init__(self, app: str, signal_name: str, args: List[str],
                 sender_class: str = None, description: str = None):
        self.app = app
        self.signal_name = signal_name
        self.args = args
        self.sender_class = sender_class or "YourModel"
        self.description = description or f"Signal sent when {signal_name.replace('_', ' ')}."

        # Derived names
        self.signal_class = ''.join(word.capitalize() for word in signal_name.split('_'))
        self.dispatch_uid = f"{app}_{signal_name}"
        self.function_name = signal_name.replace('_', ' ').split()[0]

    def generate_all(self, output_dir: Path = None):
        """Generate all signal-related files."""
        if output_dir is None:
            output_dir = Path.cwd() / self.app

        print(f"Generating signal boilerplate for: {self.signal_name}")
        print(f"App: {self.app}")
        print(f"Arguments: {', '.join(self.args)}")
        print("=" * 60)

        # Generate files
        signals_file = self._generate_signals_file()
        handler_file = self._generate_handler_file()
        sender_example = self._generate_sender_example()
        test_file = self._generate_test_file()

        # Output
        print("\n📄 signals.py (add to your app's signals.py):")
        print("-" * 60)
        print(signals_file)

        print("\n📄 handlers.py (add to your app's handlers.py):")
        print("-" * 60)
        print(handler_file)

        print("\n📄 sender_example.py (example of how to send the signal):")
        print("-" * 60)
        print(sender_example)

        print("\n📄 test_signals.py (add to your tests):")
        print("-" * 60)
        print(test_file)

        print("\n" + "=" * 60)
        print("✅ Generation complete!")
        print("\nNext steps:")
        print("1. Copy the signals.py content to your app's signals module")
        print("2. Copy the handlers.py content to your app's handlers module")
        print("3. Import signals in your AppConfig.ready() method:")
        print(f"   import {self.app}.signals  # noqa: F401")
        print("4. Implement the handler logic")
        print("5. Add tests")
        print("6. Send the signal from your business logic")

    def _generate_signals_file(self) -> str:
        """Generate signals.py content."""
        args_doc = self._format_args_doc()
        example_args = self._format_example_args()

        return SIGNALS_FILE_TEMPLATE.format(
            app=self.app,
            signal_name=self.signal_name,
            signal_description=self.description,
            docstring=self.description,
            args_doc=args_doc,
            sender_class=self.sender_class,
            example_args=example_args
        )

    def _generate_handler_file(self) -> str:
        """Generate handler code."""
        args_str = ', '.join(self.args)
        handler_args_doc = '\n'.join(
            f"        {arg}: Description of {arg}"
            for arg in self.args
        )

        return HANDLER_TEMPLATE.format(
            app=self.app,
            signal_name=self.signal_name,
            dispatch_uid=self.dispatch_uid,
            args=args_str,
            handler_args_doc=handler_args_doc
        )

    def _generate_sender_example(self) -> str:
        """Generate example sender code."""
        example_args = self._format_example_args()

        # Generate example instance creation
        example_lines = []
        for arg in self.args:
            if arg == self.signal_name.split('_')[0]:
                example_lines.append(f"    {arg} = {self.sender_class}.objects.get(pk=1)")
            else:
                example_lines.append(f"    {arg} = ...  # Your value here")

        example_instance_creation = '\n'.join(example_lines)

        return SENDER_EXAMPLE_TEMPLATE.format(
            app=self.app,
            signal_name=self.signal_name,
            sender_class=self.sender_class,
            example_instance_creation=example_instance_creation,
            example_args=example_args
        )

    def _generate_test_file(self) -> str:
        """Generate test template."""
        args_str = ', '.join(self.args)

        test_received_dict = '\n'.join(
            f"                '{arg}': {arg},"
            for arg in self.args
        )

        example_handler_call = ', '.join(
            f"{arg}=..."
            for arg in self.args
        )

        return TEST_TEMPLATE.format(
            app=self.app,
            signal_name=self.signal_name,
            signal_class=self.signal_class,
            args=args_str,
            test_received_dict=test_received_dict,
            function_name=self.function_name,
            example_handler_call=example_handler_call
        )

    def _format_args_doc(self) -> str:
        """Format arguments documentation."""
        lines = [f"    sender: The sender class (usually {self.sender_class})"]
        for arg in self.args:
            lines.append(f"    {arg}: Description of {arg}")
        return '\n'.join(lines)

    def _format_example_args(self, indent=8) -> str:
        """Format example arguments for signal.send()."""
        lines = []
        for arg in self.args:
            if arg == self.signal_name.split('_')[0]:
                lines.append(f"{' ' * indent}{arg}={arg},")
            else:
                lines.append(f"{' ' * indent}{arg}=...,  # Your value")
        return '\n'.join(lines)

    def write_to_files(self, app_dir: Path):
        """Write generated code to actual files."""
        app_path = Path(app_dir)

        if not app_path.exists():
            print(f"Error: App directory not found: {app_path}")
            return

        # Create/update signals.py
        signals_file = app_path / 'signals.py'
        signals_content = self._generate_signals_file()

        if signals_file.exists():
            print(f"⚠️  {signals_file} already exists. Append the following:")
            print(signals_content)
        else:
            signals_file.write_text(signals_content)
            print(f"✅ Created {signals_file}")

        # Create/update handlers.py
        handlers_file = app_path / 'handlers.py'
        handler_content = self._generate_handler_file()

        if handlers_file.exists():
            print(f"⚠️  {handlers_file} already exists. Append the following:")
            print(handler_content)
        else:
            handlers_file.write_text(handler_content)
            print(f"✅ Created {handlers_file}")

        # Create example file
        example_file = app_path / f'{self.signal_name}_example.py'
        example_content = self._generate_sender_example()
        example_file.write_text(example_content)
        print(f"✅ Created {example_file}")

        # Create/update tests
        tests_dir = app_path / 'tests'
        if not tests_dir.exists():
            tests_dir.mkdir()
            (tests_dir / '__init__.py').touch()

        test_file = tests_dir / f'test_{self.signal_name}.py'
        test_content = self._generate_test_file()

        if test_file.exists():
            print(f"⚠️  {test_file} already exists. Append the following:")
            print(test_content)
        else:
            test_file.write_text(test_content)
            print(f"✅ Created {test_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate Django signal boilerplate code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a payment_completed signal
  python generate_signal.py --app payments --signal payment_completed \\
      --args "payment,amount,transaction_id" --sender Payment

  # Generate an order_shipped signal
  python generate_signal.py --app orders --signal order_shipped \\
      --args "order,tracking_number,carrier" --sender Order

  # Write to files
  python generate_signal.py --app payments --signal payment_completed \\
      --args "payment,amount" --write
        """
    )

    parser.add_argument(
        '--app',
        required=True,
        help='Django app name (e.g., myapp)'
    )
    parser.add_argument(
        '--signal',
        required=True,
        help='Signal name in snake_case (e.g., payment_completed, order_shipped)'
    )
    parser.add_argument(
        '--args',
        required=True,
        help='Comma-separated list of signal arguments (e.g., "payment,amount,transaction_id")'
    )
    parser.add_argument(
        '--sender',
        help='Sender class name (default: YourModel)'
    )
    parser.add_argument(
        '--description',
        help='Signal description (default: auto-generated)'
    )
    parser.add_argument(
        '--write',
        action='store_true',
        help='Write generated code to files (default: print to stdout)'
    )
    parser.add_argument(
        '--app-dir',
        help='Path to app directory (default: current directory / app name)'
    )

    args = parser.parse_args()

    # Parse arguments list
    signal_args = [arg.strip() for arg in args.args.split(',')]

    # Validate signal name
    if not args.signal.replace('_', '').isalnum():
        print("Error: Signal name must be in snake_case (letters, numbers, underscores only)")
        sys.exit(1)

    # Create generator
    generator = SignalGenerator(
        app=args.app,
        signal_name=args.signal,
        args=signal_args,
        sender_class=args.sender,
        description=args.description
    )

    # Generate
    if args.write:
        app_dir = args.app_dir or Path.cwd() / args.app
        generator.write_to_files(Path(app_dir))
    else:
        generator.generate_all()


if __name__ == '__main__':
    main()
