#!/bin/sh
set -eu
umask 077

fail() { printf 'Tracker error: %s\n' "$1" >&2; exit 1; }
action= account= message= owner= stage= receipt= reason= source= state_root=
while [ "$#" -gt 0 ]; do
    [ "$#" -ge 2 ] || fail "Arguments require values."
    case "$1" in
        --action) action=$2 ;; --account) account=$2 ;; --message) message=$2 ;;
        --owner) owner=$2 ;; --stage) stage=$2 ;; --receipt) receipt=$2 ;;
        --reason) reason=$2 ;; --source) source=$2 ;; --state-root) state_root=$2 ;;
        *) fail "Unknown argument." ;;
    esac
    shift 2
done
case "$action" in
    init|acquire|heartbeat|release|claim|status|list-open|begin|confirm|retry-stage|block|retry|complete) ;;
    artifact-begin|artifact-status|artifact-confirm|artifact-list) ;;
    *) fail "Unsupported action." ;;
esac
case "$stage" in ''|estimate|draft|teams) ;; *) fail "Unsupported stage." ;; esac
case "$reason" in
    ''|unreadable_requirements|permission_restriction|ambiguous_recipient|uncertain_outcome|delivery_failed|other) ;;
    *) fail "Unsupported block reason." ;;
esac
[ -n "$account" ] || fail "Account identity is required."
# AAD IDs and UPNs are ASCII; avoid locale-dependent account normalization.
LC_ALL=C
export LC_ALL
case "$account" in *[![:print:]]*) fail "Use an ASCII AAD identity or UPN." ;; esac
account=$(printf '%s' "$account" | LC_ALL=C tr '[:upper:]' '[:lower:]' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
[ -n "$account" ] || fail "Account identity is required."
case "$action" in
    init|status) ;;
    *) [ "${#owner}" -eq 32 ] || fail "A 32-character owner token is required." ;;
esac
[ -z "$owner" ] || [ "${#owner}" -eq 32 ] || fail "Invalid owner token length."
case "$owner" in *[!0-9a-f]*) fail "Invalid owner token." ;; esac
case "$action" in
    claim|status|begin|confirm|retry-stage|block|retry|complete|artifact-begin|artifact-status|artifact-confirm|artifact-list)
        [ -n "$message" ] || fail "Source message identity is required." ;;
esac
case "$action" in
    begin|confirm|retry-stage) [ -n "$stage" ] || fail "Stage is required." ;;
esac
case "$action" in
    confirm|artifact-begin|artifact-confirm) [ -n "$receipt" ] || fail "Artifact receipt is required." ;;
esac
case "$action" in
    artifact-begin|artifact-status|artifact-confirm) [ -n "$source" ] || fail "Artifact source identity is required." ;;
    *) [ -z "$source" ] || fail "Source is only supported for single-artifact actions." ;;
esac
if [ "$action" = artifact-confirm ]; then
    saved_id=$(printf '%s' "$receipt" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [ -n "$saved_id" ] || fail "An immutable saved estimate ID is required."
    case "$saved_id" in
        *://*|//*|[Ww][Ww][Ww].*|[Hh][Tt][Tt][Pp]:*|[Hh][Tt][Tt][Pp][Ss]:*)
            fail "Use the immutable saved estimate ID, not a share URL." ;;
    esac
fi
[ "$action" != block ] || [ -n "$reason" ] || fail "Block reason is required."
command -v sqlite3 >/dev/null 2>&1 || fail "SQLite is unavailable; no installation was attempted."
command -v shasum >/dev/null 2>&1 || fail "SHA-256 is unavailable; no installation was attempted."
hash() { printf '%s' "$1" | shasum -a 256 | cut -d ' ' -f 1; }
account_hash=$(hash "$account")
message_hash= receipt_hash= source_hash=
[ -z "$message" ] || message_hash=$(hash "$message")
[ -z "$receipt" ] || receipt_hash=$(hash "$receipt")
[ -z "$source" ] || source_hash=$(hash "$source")
if [ -z "$state_root" ]; then
    [ "$(uname -s)" = Darwin ] || fail "Default path supports macOS; use the Windows adapter on Windows."
    state_root="$HOME/Library/Application Support/Microsoft Scout/skill-state/azure-pricing-estimator"
fi
case "$state_root" in /*) ;; *) fail "State root must be absolute." ;; esac
directory="$state_root/$account_hash"
db="$directory/tracker.sqlite3"
marker="$directory/initialized-v1"
artifact_marker="$directory/initialized-artifacts-v1"
for path in "$state_root" "$directory" "$db" "$marker" "$artifact_marker"; do
    [ ! -L "$path" ] || fail "Tracker paths must not be symbolic links."
done
for path in "$state_root" "$directory"; do
    [ ! -e "$path" ] || [ -d "$path" ] || fail "Tracker directory path has the wrong type."
done
for path in "$db" "$marker" "$artifact_marker"; do
    [ ! -e "$path" ] || [ -f "$path" ] || fail "Tracker file path has the wrong type."
done
[ ! -s "$marker" ] || fail "Tracker initialization marker is invalid."
[ ! -s "$artifact_marker" ] || fail "Tracker artifact marker is invalid."
artifacts_required=0
[ ! -f "$artifact_marker" ] || artifacts_required=1
for suffix in -journal -wal -shm; do
    path="$db$suffix"
    [ ! -L "$path" ] || fail "SQLite sidecar must not be a symbolic link."
    [ ! -e "$path" ] || [ -f "$path" ] || fail "SQLite sidecar has the wrong type."
done
if [ "$action" = init ]; then
    if { [ -e "$marker" ] || [ -e "$artifact_marker" ]; } && [ ! -f "$db" ]; then
        fail "Initialized tracker is missing. Restore it; do not reset processing history."
    fi
    if [ -e "$db" ] && [ ! -s "$db" ]; then
        fail "Existing tracker is empty. Refusing to recreate history."
    fi
    mkdir -p "$directory"
    chmod 700 "$directory"
else
    [ -f "$db" ] && [ -f "$marker" ] || fail "Tracker is not initialized or is missing."
    [ -f "$artifact_marker" ] || fail "Run init to upgrade the tracker artifact checkpoints."
fi
scripts=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ -f "$scripts/schema.sql" ] && [ -f "$scripts/tracker.sql" ] || fail "Packaged SQL resources are missing."

# Only validated ASCII enums and SHA-256 hashes enter the SQL template.
sql=$(sed \
    -e "s/__ACTION__/$action/g" -e "s/__MESSAGE__/$message_hash/g" \
    -e "s/__OWNER__/$owner/g" -e "s/__STAGE__/$stage/g" \
    -e "s/__RECEIPT__/$receipt_hash/g" -e "s/__REASON__/$reason/g" \
    -e "s/__SOURCE__/$source_hash/g" \
    "$scripts/tracker.sql")
if [ "$action" = init ]; then
    schema=$(sed -e "s/__ARTIFACTS_REQUIRED__/$artifacts_required/g" \
        -e "s/__OWNER__/$owner/g" "$scripts/schema.sql")
else
    schema=
fi
mode=rw
if [ "$action" = init ] && [ ! -e "$db" ]; then mode=rwc; fi
uri_path=$(printf '%s' "$db" | sed 's/%/%25/g;s/?/%3F/g;s/#/%23/g')
# Capture output until COMMIT succeeds, so a failed write never returns a receipt.
if ! result=$(printf '%s\n%s\n' "$schema" "$sql" |
    sqlite3 -batch -bail -noheader -separator '|' -cmd '.timeout 10000' "file:$uri_path?mode=$mode"); then
    fail "SQLite operation failed. Processing must stop; retain the existing tracker."
fi
chmod 600 "$db"
if [ "$action" = init ]; then
    touch "$marker" "$artifact_marker"
    chmod 600 "$marker" "$artifact_marker"
fi
if { [ "$action" != list-open ] && [ "$action" != artifact-list ]; } || [ -n "$result" ]; then
    printf '%s\n' "$result"
fi
