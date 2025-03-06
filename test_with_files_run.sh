#!/bin/bash

# Script for testing files found condition

# Path to the test directory with a file
MEDIA_DIR="./test_with_files"

# Path to the project root
PROJECT_DIR="/Users/alex/Library/CloudStorage/GoogleDrive-asalazar.personal@gmail.com/My Drive/Projects/transcribe"

# First clear any existing log
rm -f ~/Library/Logs/transcribe.log

# Run the transcription batch process and capture output
cd "$PROJECT_DIR"
OUTPUT=$(python -m transcribe batch "$MEDIA_DIR" 2>&1)

# Only log if output contains information about processing files
if [[ $OUTPUT == *"new media files to process"* ]]; then
  echo "$OUTPUT" >> ~/Library/Logs/transcribe.log
  echo "Batch process completed at $(date)" >> ~/Library/Logs/transcribe.log
fi

# Check if log was created
echo "After execution, log exists:"
ls -la ~/Library/Logs/transcribe.log 2>/dev/null || echo "No log file created - something went wrong!"

# Display log contents if it exists
if [ -f ~/Library/Logs/transcribe.log ]; then
  echo
  echo "Log contents:"
  cat ~/Library/Logs/transcribe.log
fi 