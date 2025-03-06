"""
Transcribe - A simple media transcription tool using AssemblyAI

This package provides functionality to transcribe audio and video files
with speaker diarization (identifying who said what).
"""

__version__ = "0.1.0"

from transcribe.core import transcribe_audio_file
from transcribe.batch import process_folder

# Define the main entry point for command-line usage
def main():
    """Entry point for the CLI when installed as a package."""
    from transcribe.cli import cli_main
    cli_main()
