#!/bin/bash
#
# Simplified wrapper script for transcribe
# This script activates the virtual environment and passes arguments to the Python module
#

# Environment setup
PROJECT_DIR="/Users/alex/Library/CloudStorage/GoogleDrive-asalazar.personal@gmail.com/My Drive/Projects/transcribe"
LOG_DIR="${HOME}/Library/Logs/transcribe"
mkdir -p "${LOG_DIR}"

# Save current working directory for relative path resolution
ORIGINAL_DIR="$(pwd)"

# Log start with timestamp
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting transcribe wrapper"

# Convert relative paths to absolute paths while preserving arguments with spaces
CONVERTED_ARGS=()
for ((i=1; i<=$#; i++)); do
    arg="${!i}"
    
    # Check if previous argument indicates this is a file path
    if [[ $i -gt 1 ]]; then
        prev_i=$((i-1))
        prev_arg="${!prev_i}"
        if [[ "$prev_arg" == "file" ]] || [[ "$prev_arg" == "batch" ]] || [[ "$prev_arg" == "--output" ]] || [[ "$prev_arg" == "-o" ]] || [[ "$prev_arg" == "--output-dir" ]] || [[ "$prev_arg" == "-d" ]]; then
            # Convert relative path to absolute path
            if [[ "$arg" != /* ]]; then
                arg="${ORIGINAL_DIR}/${arg}"
            fi
        fi
    fi
    
    CONVERTED_ARGS+=("$arg")
done

# Change to project directory
cd "${PROJECT_DIR}" || { 
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Cannot change to project directory"
    exit 1
}

# Activate virtual environment if it exists
if [ -d "${PROJECT_DIR}/.venv" ]; then
    source "${PROJECT_DIR}/.venv/bin/activate"
fi

# Check for API key
if [ -z "${ASSEMBLY_API_KEY}" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: ASSEMBLY_API_KEY not set"
    echo "Please set your AssemblyAI API key with: export ASSEMBLY_API_KEY='your_key'"
    exit 1
fi

# Run the command with converted arguments
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running: python -m transcribe ${CONVERTED_ARGS[@]}"
python -m transcribe "${CONVERTED_ARGS[@]}"
EXIT_CODE=$?

# Log completion
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Finished with exit code: ${EXIT_CODE}"
exit ${EXIT_CODE}
