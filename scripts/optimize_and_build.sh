#!/bin/bash
# Optimize a resume and build Word/PDF outputs in one step.
#
# Usage:
#   ./scripts/optimize_and_build.sh <job_description_url> [--company COMPANY] [--verbose]

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <job_description_url> [--company COMPANY] [--verbose]"
    exit 1
fi

JOB_URL="$1"
shift

python3 "$(dirname "$0")/_optimize_and_build.py" "$JOB_URL" "$@"
