#!/bin/sh
log() {
    echo "$*" 1>&2
}
log_info() {
    log "INFO: $*"
}
log_error() {
    log "ERROR: $*"
}

log_info "Test build artifact"
# run list devices command to test pyinstaller
PROGRAM_PATH="$(dirname "$0")/dist/vznncv-stlink-tools-wrapper"
if [ ! -f "$PROGRAM_PATH" ]; then
    log_error "Artifact \"${PROGRAM_PATH}\" does not exists"
    exit 1
fi
# run command
log_info "test show-devices ..."
"${PROGRAM_PATH}" show-devices --format json
ret_code="$?"
if [ "$ret_code" -ne 0 ]; then
    log_error "Test failed!"
    exit 1
fi

log_info "Complete"
