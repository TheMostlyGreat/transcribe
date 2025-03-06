"""
Entry point for running transcribe as a module.
"""

import sys
from transcribe.cli import cli_main

if __name__ == "__main__":
    sys.exit(cli_main()) 