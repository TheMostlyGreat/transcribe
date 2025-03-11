"""
Transcribe - A simple media transcription tool using AssemblyAI

This package provides functionality to transcribe audio and video files
with speaker diarization (identifying who said what).
"""

import logging

# Import version from separate file to avoid circular imports
try:
    from .version import __version__
except ImportError:
    # Fallback for situations where imports fail (like during testing)
    __version__ = "0.1"

# Import key functionality to make it available at the package level
try:
    from transcribe.core import transcribe_audio_file
    from transcribe.batch import process_folder
except ImportError:
    # Handle partially imported state during testing
    pass

def get_logger(name: str = None) -> logging.Logger:
    """
    Get a configured logger that writes to both console and log file.
    
    The log file configuration happens when the CLI is initialized through
    the setup_logging function. This function returns a logger that will
    inherit that configuration.
    
    Args:
        name: The name for the logger (typically the module name)
        
    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)

# Define the main entry point for command-line usage
def main():
    """Entry point for the CLI when installed as a package."""
    from transcribe.cli import cli_main
    return cli_main()
