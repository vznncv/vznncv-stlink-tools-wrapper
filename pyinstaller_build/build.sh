#!/usr/bin/env bash
# helper script to build standalone executable file with a pyinstaller
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROGRAM_NAME="vznncv-stlink"
PROJECT_SRC=$(realpath "$SCRIPT_DIR/../src")
DIST_DIR="$SCRIPT_DIR/dist"

log_info() {
    echo "INFO: $*" >&2
}
log_err() {
    echo "ERROR: $*" >&2
}

(
    cd "$SCRIPT_DIR"
    pyinstaller --clean --noconfirm --onefile --name "$PROGRAM_NAME" --paths "$PROJECT_SRC" "entry_point.py"
)

executable_filename="$PROGRAM_NAME"
if [[ ! -f "$DIST_DIR/$executable_filename" ]]; then
    executable_filename="${executable_filename}.exe"
fi
if [[ ! -f "$DIST_DIR/$executable_filename" ]]; then
    log_err "Cannot find build artifact in the \"$DIST_DIR\" directory"
    exit 1
fi
# copy artifact
cp "$DIST_DIR/$executable_filename" "$SCRIPT_DIR/$executable_filename"

log_info "Complete"
