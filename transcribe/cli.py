"""
Command-line interface for the transcribe package.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, List

from transcribe import __version__
from transcribe.core import transcribe_audio_file, SUPPORTED_EXTENSIONS
from transcribe.batch import process_folder


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging based on verbosity level.
    
    Args:
        verbose: Whether to enable verbose (DEBUG) logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configure root logger - force set level
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear any existing handlers
    if not root_logger.handlers:
        # Add a handler if none exists
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)


def display_supported_formats() -> str:
    """
    Format the supported file extensions for display.
    
    Returns:
        str: Formatted string of supported extensions
    """
    extensions = sorted(list(SUPPORTED_EXTENSIONS))
    return ", ".join(ext.lstrip('.') for ext in extensions)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Args:
        args: Command-line arguments (uses sys.argv if None)
        
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description=f"Transcribe v{__version__}: Convert audio and video files to text with speaker diarization.",
        epilog=f"Supported formats: {display_supported_formats()}",
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Single file transcription command
    transcribe_parser = subparsers.add_parser(
        "file", 
        help="Transcribe a single media file"
    )
    transcribe_parser.add_argument(
        "media_file", 
        help="Path to the input audio or video file"
    )
    transcribe_parser.add_argument(
        "--output", "-o",
        help="Custom output file path (default: same location as input with _transcription.md suffix)",
    )
    
    # Batch processing command
    batch_parser = subparsers.add_parser(
        "batch", 
        help="Process multiple files in a directory"
    )
    batch_parser.add_argument(
        "directory", 
        help="Directory containing media files to transcribe"
    )
    batch_parser.add_argument(
        "--email", "-e",
        action="store_true",
        help="Send email notifications when transcriptions complete",
    )
    
    # Global options
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    # Parse arguments
    parsed_args = parser.parse_args(args)
    
    # Default to file command if no command specified but media_file is provided
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists() and parsed_args.command is None:
        parsed_args.command = "file"
        parsed_args.media_file = sys.argv[1]
    
    return parsed_args


def cli_main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the command-line interface.
    
    Args:
        args: Command-line arguments (uses sys.argv if None)
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse arguments
    parsed_args = parse_args(args)
    
    # Setup logging
    setup_logging(parsed_args.verbose)
    
    # Get logger for this module
    logger = logging.getLogger(__name__)
    
    # Process commands
    if parsed_args.command == "file":
        # Transcribe a single file
        result = transcribe_audio_file(
            parsed_args.media_file,
            output_path=getattr(parsed_args, "output", None),
        )
        return 0 if result else 1
        
    elif parsed_args.command == "batch":
        # Process files in a directory
        send_emails = getattr(parsed_args, "email", False)
        success, processed_count = process_folder(
            parsed_args.directory,
            send_emails=send_emails,
        )
        return 0 if success else 1
        
    else:
        # No command specified
        logger.error("No command specified. Use 'file' or 'batch' command.")
        return 1


if __name__ == "__main__":
    sys.exit(cli_main()) 