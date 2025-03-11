#!/bin/bash
# Test script for verifying the "no files found" scenario in batch processing

# Path to the empty test directory
MEDIA_DIR="./tests/test_data/empty_dir"

# Path to the project root - do not escape spaces when using quotes
PROJECT_DIR="$(pwd)"

# First clear any existing log
rm -f ~/Library/Logs/transcribe.log

echo "Running batch processor on empty directory: $MEDIA_DIR"

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
ls -la ~/Library/Logs/transcribe.log 2>/dev/null || echo "No log file - Good! No logging occurred." 