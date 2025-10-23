#!/bin/bash
set -euo pipefail

PROJECT_DIR="/Users/alex/Library/CloudStorage/GoogleDrive-asalazar.personal@gmail.com/My Drive/Projects/transcribe"
ORIGINAL_DIR="$(pwd)"

# Convert relative paths after file/batch commands to absolute
args=()
prev=""
for arg in "$@"; do
    if [[ "$prev" =~ ^(file|batch|-[od]|--output(|-dir))$ ]] && [[ "$arg" != /* ]]; then
        args+=("${ORIGINAL_DIR}/${arg}")
    else
        args+=("$arg")
    fi
    prev="$arg"
done

cd "${PROJECT_DIR}"
[[ -d .venv ]] && source .venv/bin/activate

if [[ -z "${ASSEMBLY_API_KEY:-}" ]]; then
    echo "ERROR: ASSEMBLY_API_KEY not set" >&2
    exit 1
fi

exec python -m transcribe "${args[@]}"
