#!/usr/bin/env python3
"""
Test script to verify progress tracking and stalled job detection.

This script simulates different scenarios for media file processing:
1. A new file being discovered
2. A file currently in progress
3. A stalled/timed-out job
4. A completed transcription job

It can also simulate a subsequent cron run to test how the system handles each scenario.
"""

import os
import sys
import time
import json
import logging
import argparse
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("test_status_tracking")

# Constants - match values from the main application
TEST_DIR = Path(__file__).parent / "test_data" / "status_tracking"
TEST_MEDIA_FILE = "test_audio.mp3"
MAX_IN_PROGRESS_AGE_HOURS = 24  # Match the value in batch.py


def create_test_environment():
    """
    Create a test environment with media file and directories.
    
    Returns:
        tuple: (test_dir, media_dir, output_dir) as Path objects
    """
    # Create test directory
    test_dir = TEST_DIR
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    media_dir = test_dir / "media"
    media_dir.mkdir()
    
    output_dir = test_dir / "output"
    output_dir.mkdir()
    
    # Get path to test audio file
    source_audio = Path(__file__).parent / "test_data" / TEST_MEDIA_FILE
    
    # Copy test audio file to media directory
    if source_audio.exists():
        shutil.copy(source_audio, media_dir / TEST_MEDIA_FILE)
    else:
        # Create a dummy audio file if the test file doesn't exist
        with open(media_dir / TEST_MEDIA_FILE, "wb") as f:
            f.write(b"dummy audio data")
    
    logger.info(f"Created test environment in {test_dir}")
    return test_dir, media_dir, output_dir


def simulate_in_progress_file(media_dir, stalled=False):
    """
    Simulate a file that's in progress (or stalled).
    
    Args:
        media_dir (Path): Directory containing media files
        stalled (bool): Whether to simulate a stalled job
        
    Returns:
        Path: Path to the created status JSON file
    """
    media_file = media_dir / TEST_MEDIA_FILE
    json_path = media_file.with_suffix('.json')
    
    # Determine start time
    start_time = time.time()
    if stalled:
        # Make it appear older than MAX_IN_PROGRESS_AGE_HOURS
        start_time = time.time() - (MAX_IN_PROGRESS_AGE_HOURS * 60 * 60 + 60)
    
    # Create the in-progress status file
    status_data = {
        "status": "in_progress",
        "media_file": str(media_file),
        "start_time": start_time,
        "message": "Transcription in progress"
    }
    
    # Optionally add a transcript ID to simulate a real job
    if stalled:
        status_data["transcript_id"] = "mock-transcript-id-123456"
    
    with open(json_path, 'w') as f:
        json.dump(status_data, f, indent=2)
    
    timestamp = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"Created {'stalled' if stalled else 'in-progress'} status file (timestamp: {timestamp})")
    
    return json_path


def simulate_completed_transcription(json_path):
    """
    Simulate a completed transcription by updating the status file.
    
    Args:
        json_path (Path): Path to the status JSON file
        
    Returns:
        Path: Path to the created MD file
    """
    with open(json_path, 'r') as f:
        status_data = json.load(f)
    
    # Remove status and add completed data
    if "status" in status_data:
        del status_data["status"]
    
    status_data["completed_time"] = time.time()
    status_data["text"] = "This is a simulated transcription result."
    status_data["duration"] = 10.5
    
    with open(json_path, 'w') as f:
        json.dump(status_data, f, indent=2)
    
    # Create a MD file too
    md_path = Path(json_path).with_suffix('.md')
    with open(md_path, 'w') as f:
        f.write("# Simulated Transcription\n\n")
        f.write("This is a simulated transcription result.")
    
    logger.info(f"Simulated completed transcription")
    
    return md_path


def run_batch_simulation(media_dir):
    """
    Run a simplified simulation of batch.py's find_new_media_files function.
    
    Args:
        media_dir (Path): Directory containing media files
        
    Returns:
        dict: Dictionary containing lists of files in different states
    """
    # Calculate the cutoff time for stalled jobs
    stalled_cutoff = time.time() - (MAX_IN_PROGRESS_AGE_HOURS * 60 * 60)
    
    # Initialize lists for different file states
    in_progress_files = []
    stalled_files = []
    new_files = []
    completed_files = []
    
    # Supported audio extensions
    supported_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg']
    
    for file_path in media_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            # Check if a status file exists
            json_path = file_path.with_suffix('.json')
            md_path = file_path.with_name(f"{file_path.stem}_transcription.md")
            
            if json_path.exists():
                try:
                    # Read the status file
                    with open(json_path, 'r') as f:
                        status_data = json.load(f)
                    
                    # Check the status
                    if "status" in status_data:
                        if status_data["status"] in ["in_progress", "processing"]:
                            # Check if it's stalled
                            start_time = status_data.get("start_time", 0)
                            if start_time < stalled_cutoff:
                                stalled_files.append((file_path, json_path))
                                logger.warning(f"Found stalled transcription: {file_path.name}")
                            else:
                                in_progress_files.append((file_path, json_path))
                                logger.info(f"Found in-progress transcription: {file_path.name}")
                        elif status_data["status"] == "error":
                            logger.warning(f"Found failed transcription: {file_path.name}")
                            new_files.append((file_path, json_path))
                    else:
                        # No status field means it's complete
                        completed_files.append((file_path, json_path))
                        logger.info(f"Found completed transcription: {file_path.name}")
                except Exception as e:
                    logger.error(f"Error reading JSON for {file_path.name}: {e}")
                    new_files.append((file_path, json_path))
            else:
                # No JSON exists
                if md_path.exists():
                    completed_files.append((file_path, md_path))
                    logger.info(f"Found completed transcription (MD only): {file_path.name}")
                else:
                    new_files.append((file_path, json_path))
                    logger.info(f"Found new media file: {file_path.name}")
    
    return {
        "in_progress": in_progress_files,
        "stalled": stalled_files,
        "new": new_files,
        "completed": completed_files
    }


def simulate_processing_stalled_file(media_file, json_path):
    """
    Simulate processing a stalled file.
    
    Args:
        media_file (Path): Path to the media file
        json_path (Path): Path to the status JSON file
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    logger.info(f"Processing stalled file: {media_file.name}")
    
    # Read the status file
    with open(json_path, 'r') as f:
        status_data = json.load(f)
    
    # Check if it has a transcript ID
    transcript_id = status_data.get("transcript_id")
    
    if transcript_id:
        logger.info(f"Found transcript ID: {transcript_id}")
        logger.info(f"Simulating AssemblyAI API check for transcript status")
        
        # Simulate an API call to AssemblyAI
        logger.info(f"AssemblyAI API indicates the transcript is complete")
        
        # Update the status file as completed
        simulate_completed_transcription(json_path)
        return True
    else:
        logger.info(f"No transcript ID found, would start a new transcription")
        # In a real scenario, we would start a new transcription here
        return False


def main():
    """Main function to run the test script."""
    parser = argparse.ArgumentParser(description="Test status tracking and stalled job handling")
    parser.add_argument(
        "--scenario", 
        choices=["new", "in_progress", "stalled", "completed"], 
        default="stalled", 
        help="Test scenario to run"
    )
    parser.add_argument(
        "--simulate-cron", 
        action="store_true", 
        help="Simulate a subsequent cron run"
    )
    args = parser.parse_args()
    
    # Create test environment
    test_dir, media_dir, output_dir = create_test_environment()
    
    # Run the selected scenario
    if args.scenario == "new":
        logger.info("Testing scenario: New file")
        # No additional setup needed - we start with a clean environment
        
    elif args.scenario == "in_progress":
        logger.info("Testing scenario: In-progress file")
        json_path = simulate_in_progress_file(media_dir, stalled=False)
        
    elif args.scenario == "stalled":
        logger.info("Testing scenario: Stalled file")
        json_path = simulate_in_progress_file(media_dir, stalled=True)
        
    elif args.scenario == "completed":
        logger.info("Testing scenario: Completed file")
        json_path = simulate_in_progress_file(media_dir, stalled=False)
        simulate_completed_transcription(json_path)
    
    # Simulate a cron run if requested
    if args.simulate_cron:
        logger.info("\n=== Simulating subsequent cron run ===\n")
        
        # Run batch simulation
        files = run_batch_simulation(media_dir)
        
        # Print summary
        logger.info("\n=== Batch Processing Summary ===")
        logger.info(f"New files to process: {len(files['new'])}")
        logger.info(f"In-progress files: {len(files['in_progress'])}")
        logger.info(f"Stalled files: {len(files['stalled'])}")
        logger.info(f"Completed files: {len(files['completed'])}")
        
        # Process stalled files if any
        for media_file, json_path in files["stalled"]:
            success = simulate_processing_stalled_file(media_file, json_path)
            logger.info(f"Stalled file processing {'successful' if success else 'pending new transcription'}")
    
    logger.info("\nTest completed. Examine the files in the test directory for results.")


if __name__ == "__main__":
    main() 