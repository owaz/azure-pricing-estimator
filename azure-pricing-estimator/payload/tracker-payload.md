# Bundled tracker payload (generated)

Load only when bootstrapping missing helpers; see reference/tracker-operations.md.
Recreate exact UTF-8 bytes with LF endings and a trailing newline, without fences.
Maintainer: regenerate each SHA-256 over exact UTF-8 script bytes (LF, trailing newline), then replace its hash and block together.

Resource: scripts/tracker.sh
SHA-256: 3a6d01dd0f7514854681683d2bc8597c821ba3bf2fe799fcc5f615162b27abd6
````text
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
````

Resource: scripts/tracker.ps1
SHA-256: a7ad24b540e0c7f63498a007b55f9f51183ab5092a3dfe7f88d538d1c7c9d570
````text
param(
    [string] $Action,
    [string] $Account,
    [string] $Message = '',
    [string] $Owner = '',
    [string] $Stage = '',
    [string] $Receipt = '',
    [string] $Reason = '',
    [string] $Source = '',
    [string] $StateRoot = ''
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$script:FailureMessage = 'Tracker operation failed.'
$database = $null

function Stop-Tracker([string] $Text) {
    $script:FailureMessage = $Text
    throw [System.InvalidOperationException]::new($Text)
}

function Get-Hash([string] $Text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        return [System.BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Test-SafeEntry([string] $Path, [bool] $Directory) {
    try {
        $attributes = [System.IO.File]::GetAttributes($Path)
    }
    catch [System.IO.FileNotFoundException] { return $false }
    catch [System.IO.DirectoryNotFoundException] { return $false }
    if (($attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        Stop-Tracker 'Tracker paths must not be symbolic links or reparse points.'
    }
    if ((($attributes -band [System.IO.FileAttributes]::Directory) -ne 0) -ne $Directory) {
        Stop-Tracker 'A tracker path has the wrong file type.'
    }
    return $true
}

function New-PrivateAcl([bool] $Directory) {
    if ($Directory) {
        $acl = New-Object System.Security.AccessControl.DirectorySecurity
        $inheritance = [System.Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
    }
    else {
        $acl = New-Object System.Security.AccessControl.FileSecurity
        $inheritance = [System.Security.AccessControl.InheritanceFlags]::None
    }
    $acl.SetOwner($script:UserSid)
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($sid in @($script:UserSid, $script:SystemSid)) {
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $sid,
            [System.Security.AccessControl.FileSystemRights]::FullControl,
            $inheritance,
            [System.Security.AccessControl.PropagationFlags]::None,
            [System.Security.AccessControl.AccessControlType]::Allow
        )
        $acl.AddAccessRule($rule)
    }
    return $acl
}

function Set-PrivateEntry([string] $Path, [bool] $Directory) {
    $script:FailureMessage = 'Could not secure tracker permissions.'
    if (-not (Test-SafeEntry $Path $Directory)) {
        Stop-Tracker 'A tracker path disappeared.'
    }
    if ($script:WindowsHost) {
        $existing = Get-Acl -LiteralPath $Path
        if ($existing.GetOwner([System.Security.Principal.SecurityIdentifier]).Value -cne $script:UserSid.Value) {
            Stop-Tracker 'The tracker path is not owned by the current user.'
        }
        Set-Acl -LiteralPath $Path -AclObject (New-PrivateAcl $Directory)
        $verified = Get-Acl -LiteralPath $Path
        if (-not $verified.AreAccessRulesProtected) {
            Stop-Tracker 'Tracker permissions could not be restricted.'
        }
        foreach ($rule in $verified.GetAccessRules($true, $true, [System.Security.Principal.SecurityIdentifier])) {
            if ($rule.IdentityReference.Value -cne $script:UserSid.Value -and
                $rule.IdentityReference.Value -cne $script:SystemSid.Value) {
                Stop-Tracker 'Tracker permissions include an unexpected identity.'
            }
        }
    }
    else {
        $mode = if ($Directory) { '700' } else { '600' }
        & /bin/chmod $mode $Path 2>$null
        if ($LASTEXITCODE -ne 0) {
            Stop-Tracker 'Could not restrict tracker permissions.'
        }
    }
}

try {
    $actions = @('init', 'acquire', 'heartbeat', 'release', 'claim', 'status', 'list-open', 'begin',
        'confirm', 'retry-stage', 'block', 'retry', 'complete',
        'artifact-begin', 'artifact-status', 'artifact-confirm', 'artifact-list')
    $stages = @('', 'estimate', 'draft', 'teams')
    $reasons = @('', 'unreadable_requirements', 'permission_restriction', 'ambiguous_recipient',
        'uncertain_outcome', 'delivery_failed', 'other')
    if ($args.Count -ne 0 -or $actions -cnotcontains $Action) {
        Stop-Tracker 'Provide a supported tracker action and named arguments.'
    }
    if ([string]::IsNullOrWhiteSpace($Account)) {
        Stop-Tracker 'Account is required and must be a nonblank user identity.'
    }
    if ($Account -cnotmatch '\A[\x20-\x7e]+\z') {
        Stop-Tracker 'Account must be an ASCII AAD identity or UPN.'
    }
    if ($Owner -cne '' -and $Owner -cnotmatch '\A[0-9a-f]{32}\z') {
        Stop-Tracker 'Owner must be the 32 lowercase hexadecimal characters returned by init.'
    }
    if ($stages -cnotcontains $Stage) {
        Stop-Tracker 'Stage must be estimate, draft, or teams.'
    }
    if ($reasons -cnotcontains $Reason) {
        Stop-Tracker 'Reason must be one of the supported reason codes.'
    }
    if ($Action -cnotin @('init', 'status') -and $Owner -ceq '') {
        Stop-Tracker 'This action requires the owner token returned by init.'
    }
    if ($Action -cin @('claim', 'status', 'begin', 'confirm', 'retry-stage', 'block', 'retry', 'complete',
        'artifact-begin', 'artifact-status', 'artifact-confirm', 'artifact-list') -and
        $Message -ceq '') {
        Stop-Tracker 'This action requires the source message identity.'
    }
    if ($Action -cin @('begin', 'confirm', 'retry-stage') -and $Stage -ceq '') {
        Stop-Tracker 'This action requires a stage.'
    }
    if ($Action -cin @('confirm', 'artifact-begin', 'artifact-confirm') -and $Receipt -ceq '') {
        Stop-Tracker 'Confirmation requires an artifact receipt.'
    }
    if ($Action -cin @('artifact-begin', 'artifact-status', 'artifact-confirm')) {
        if ($Source -ceq '') { Stop-Tracker 'Artifact source identity is required.' }
    }
    elseif ($Source -cne '') {
        Stop-Tracker 'Source is only supported for single-artifact actions.'
    }
    if ($Action -ceq 'artifact-confirm') {
        if ([string]::IsNullOrWhiteSpace($Receipt)) {
            Stop-Tracker 'An immutable saved estimate ID is required.'
        }
        if ($Receipt.Trim() -match '://|\A(?://|www\.|https?:)') {
            Stop-Tracker 'Use the immutable saved estimate ID, not a share URL.'
        }
    }
    if ($Action -ceq 'block' -and $Reason -ceq '') {
        Stop-Tracker 'Blocking requires a reason code.'
    }

    $script:WindowsHost = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
    $macVariable = Get-Variable -Name IsMacOS -ErrorAction SilentlyContinue
    $macHost = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::MacOSX -or
        ($null -ne $macVariable -and $macVariable.Value)
    if (-not $script:WindowsHost -and -not $macHost) {
        Stop-Tracker 'This adapter supports Windows PowerShell 5.1+ or PowerShell on macOS.'
    }
    if ($PSVersionTable.PSVersion -lt [version]'5.1') {
        Stop-Tracker 'PowerShell 5.1 or later is required.'
    }

    $script:FailureMessage = 'Could not prepare the tracker state path.'
    if ($StateRoot -ceq '') {
        if ($script:WindowsHost) {
            $base = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::LocalApplicationData)
            if ([string]::IsNullOrWhiteSpace($base)) {
                Stop-Tracker 'The local application data directory is unavailable.'
            }
            $StateRoot = Join-Path $base 'Microsoft Scout/skill-state/azure-pricing-estimator'
        }
        else {
            $base = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::UserProfile)
            if ([string]::IsNullOrWhiteSpace($base)) {
                Stop-Tracker 'The user profile directory is unavailable.'
            }
            $StateRoot = Join-Path $base 'Library/Application Support/Microsoft Scout/skill-state/azure-pricing-estimator'
        }
    }
    if (-not [System.IO.Path]::IsPathRooted($StateRoot) -or $StateRoot.Contains([char]0)) {
        Stop-Tracker 'StateRoot must be an absolute filesystem path.'
    }
    if ($script:WindowsHost -and $StateRoot -cnotmatch '\A(?:[A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+(?:[\\/]|$))') {
        Stop-Tracker 'StateRoot must be a fully qualified filesystem path.'
    }
    $StateRoot = [System.IO.Path]::GetFullPath($StateRoot)
    $accountHash = Get-Hash $Account.Trim().ToLowerInvariant()
    $accountDirectory = Join-Path $StateRoot $accountHash
    $databasePath = Join-Path $accountDirectory 'tracker.sqlite3'
    $markerPath = Join-Path $accountDirectory 'initialized-v1'
    $artifactMarkerPath = Join-Path $accountDirectory 'initialized-artifacts-v1'
    $messageHash = if ($Message -ceq '') { '' } else { Get-Hash $Message }
    $receiptHash = if ($Receipt -ceq '') { '' } else { Get-Hash $Receipt }
    $sourceHash = if ($Source -ceq '') { '' } else { Get-Hash $Source }

    $tokens = @{
        '__ACTION__' = $Action
        '__MESSAGE__' = $messageHash
        '__OWNER__' = $Owner
        '__STAGE__' = $Stage
        '__RECEIPT__' = $receiptHash
        '__REASON__' = $Reason
        '__SOURCE__' = $sourceHash
    }
    if (($messageHash -cne '' -and $messageHash -cnotmatch '\A[0-9a-f]{64}\z') -or
        ($receiptHash -cne '' -and $receiptHash -cnotmatch '\A[0-9a-f]{64}\z') -or
        ($sourceHash -cne '' -and $sourceHash -cnotmatch '\A[0-9a-f]{64}\z')) {
        Stop-Tracker 'Tracker hashing failed.'
    }
    $script:FailureMessage = 'Could not load the bundled tracker SQL or native helper.'
    $sqlPath = Join-Path $PSScriptRoot 'tracker.sql'
    $schemaPath = Join-Path $PSScriptRoot 'schema.sql'
    $sql = [System.IO.File]::ReadAllText($sqlPath)
    foreach ($token in $tokens.Keys) {
        if (-not $sql.Contains($token)) {
            Stop-Tracker 'The bundled tracker SQL has an invalid placeholder set.'
        }
        $sql = $sql.Replace($token, $tokens[$token])
    }
    if ($sql -cmatch '__[A-Z_]+__') {
        Stop-Tracker 'The bundled tracker SQL contains an unresolved placeholder.'
    }
    $schema = if ($Action -ceq 'init') { [System.IO.File]::ReadAllText($schemaPath) } else { '' }
    if ($null -eq ('ScoutPricing.NativeSqlite' -as [type])) {
        Add-Type -Path (Join-Path $PSScriptRoot 'NativeSqlite.cs')
    }

    $script:FailureMessage = 'Could not inspect the tracker state.'
    $rootExists = Test-SafeEntry $StateRoot $true
    $directoryExists = Test-SafeEntry $accountDirectory $true
    $databaseExists = Test-SafeEntry $databasePath $false
    $markerExists = Test-SafeEntry $markerPath $false
    $artifactMarkerExists = Test-SafeEntry $artifactMarkerPath $false
    if (($markerExists -or $artifactMarkerExists) -and -not $databaseExists) {
        Stop-Tracker 'Initialized tracker database is missing; refusing to recreate lost state.'
    }
    if ($databaseExists -and ([System.IO.FileInfo]::new($databasePath)).Length -eq 0) {
        Stop-Tracker 'Tracker database is empty; refusing to recreate lost state.'
    }
    if ($markerExists -and ([System.IO.FileInfo]::new($markerPath)).Length -ne 0) {
        Stop-Tracker 'Tracker initialization marker is invalid.'
    }
    if ($artifactMarkerExists -and ([System.IO.FileInfo]::new($artifactMarkerPath)).Length -ne 0) {
        Stop-Tracker 'Tracker artifact marker is invalid.'
    }
    if ($Action -cne 'init' -and (-not $databaseExists -or -not $markerExists -or -not $directoryExists)) {
        Stop-Tracker 'Tracker is not initialized; run init before using it.'
    }
    if ($Action -cne 'init' -and -not $artifactMarkerExists) {
        Stop-Tracker 'Run init to upgrade the tracker artifact checkpoints.'
    }
    if ($Action -ceq 'init') {
        $required = if ($artifactMarkerExists) { '1' } else { '0' }
        $schema = $schema.Replace('__ARTIFACTS_REQUIRED__', $required).Replace('__OWNER__', $Owner)
    }
    if ($script:WindowsHost) {
        $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
        try { $script:UserSid = $identity.User }
        finally { $identity.Dispose() }
        $script:SystemSid = [System.Security.Principal.SecurityIdentifier]::new('S-1-5-18')
    }
    if (-not $directoryExists) {
        $script:FailureMessage = 'Could not create the private tracker directory.'
        if (-not $rootExists) {
            [void][System.IO.Directory]::CreateDirectory($StateRoot)
        }
        if ($script:WindowsHost) {
            $acl = New-PrivateAcl $true
            if ($PSVersionTable.PSEdition -eq 'Desktop') {
                [void][System.IO.Directory]::CreateDirectory($accountDirectory, $acl)
            }
            else {
                [void][System.IO.FileSystemAclExtensions]::CreateDirectory($acl, $accountDirectory)
            }
        }
        else {
            [void][System.IO.Directory]::CreateDirectory($accountDirectory)
        }
    }
    Set-PrivateEntry $accountDirectory $true
    foreach ($suffix in @('-journal', '-wal', '-shm')) {
        $sidecar = $databasePath + $suffix
        if (Test-SafeEntry $sidecar $false) {
            Set-PrivateEntry $sidecar $false
        }
    }

    $fresh = -not $databaseExists
    if ($fresh) {
        $script:FailureMessage = 'Could not exclusively create the tracker database.'
        $file = [System.IO.File]::Open($databasePath, [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        $file.Dispose()
    }
    Set-PrivateEntry $databasePath $false
    if ($markerExists) { Set-PrivateEntry $markerPath $false }
    if ($artifactMarkerExists) { Set-PrivateEntry $artifactMarkerPath $false }
    if (-not $fresh -and ([System.IO.FileInfo]::new($databasePath)).Length -eq 0) {
        Stop-Tracker 'Tracker database became empty; refusing to recreate lost state.'
    }

    $script:FailureMessage = 'Could not open native SQLite; verify the OS library and tracker access.'
    $database = [ScoutPricing.NativeSqlite]::new($databasePath, $fresh, $script:WindowsHost)
    if ($Action -ceq 'init') {
        $script:FailureMessage = 'Tracker schema initialization failed; existing state was not reset.'
        [void]$database.Execute($schema)
    }
    $script:FailureMessage = 'Tracker transaction failed; do not assume the requested action succeeded.'
    $rows = @($database.Execute($sql))
    $database.Dispose()
    $database = $null
    if ($Action -cnotin @('list-open', 'artifact-list') -and $rows.Length -ne 1) {
        Stop-Tracker 'Tracker transaction returned an invalid result.'
    }
    if ($Action -ceq 'list-open') {
        foreach ($row in $rows) {
            if ($row -cnotmatch '\A[0-9a-f]{32}\|(active|blocked)(\|(pending|started|done)){3}\|[A-Za-z0-9_.:-]*\|[0-9]+\z') {
                Stop-Tracker 'Tracker listing returned an invalid result.'
            }
        }
    }
    if ($Action -cin @('artifact-begin', 'artifact-status', 'artifact-confirm', 'artifact-list')) {
        foreach ($row in $rows) {
            if ($Action -ceq 'artifact-status' -and $row -ceq 'not_found') { continue }
            if ($row -cnotmatch '\A[0-9a-f]{64}\|(?:started\|[0-9a-f]{64}\||done\|[0-9a-f]{64}\|[0-9a-f]{64})\|[0-9]+\z') {
                Stop-Tracker 'Tracker artifact checkpoint returned an invalid result.'
            }
        }
    }
    if ($Action -ceq 'init') {
        if ($rows.Length -ne 1 -or $rows[0] -cnotmatch '\Ainit\|1\|[0-9a-f]{32}\z') {
            Stop-Tracker 'Tracker initialization returned an invalid result.'
        }
        if (-not $markerExists) {
            $script:FailureMessage = 'Tracker initialized but its marker could not be saved; retry init.'
            if (-not (Test-SafeEntry $markerPath $false)) {
                $file = [System.IO.File]::Open($markerPath, [System.IO.FileMode]::CreateNew,
                    [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
                $file.Dispose()
            }
            elseif (([System.IO.FileInfo]::new($markerPath)).Length -ne 0) {
                Stop-Tracker 'Tracker initialization marker is invalid.'
            }
        }
        Set-PrivateEntry $markerPath $false
        if (-not $artifactMarkerExists) {
            $script:FailureMessage = 'Artifact schema initialized but its marker could not be saved; retry init.'
            if (-not (Test-SafeEntry $artifactMarkerPath $false)) {
                $file = [System.IO.File]::Open($artifactMarkerPath, [System.IO.FileMode]::CreateNew,
                    [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
                $file.Dispose()
            }
            elseif (([System.IO.FileInfo]::new($artifactMarkerPath)).Length -ne 0) {
                Stop-Tracker 'Tracker artifact marker is invalid.'
            }
        }
        Set-PrivateEntry $artifactMarkerPath $false
    }
    foreach ($row in $rows) { [System.Console]::Out.WriteLine($row) }
}
catch {
    [System.Console]::Error.WriteLine('Tracker error: ' + $script:FailureMessage)
    exit 1
}
finally {
    if ($null -ne $database) {
        try { $database.Dispose() }
        catch {
            [System.Console]::Error.WriteLine('Tracker error: Native SQLite cleanup failed.')
            exit 1
        }
    }
}
````

Resource: scripts/NativeSqlite.cs
SHA-256: 88f837fdf7f40366e389f0b4c959dfe2508e286f9bfb1ce2198451a75a6286a8
````text
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text;

namespace ScoutPricing
{
    public sealed class NativeSqlite : IDisposable
    {
        private const int OpenReadWrite = 2;
        private const int OpenCreate = 4;
        private readonly bool windows;
        private IntPtr database;

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        private delegate int WindowsRowCallback(IntPtr context, int count, IntPtr values, IntPtr names);

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        private delegate int MacRowCallback(IntPtr context, int count, IntPtr values, IntPtr names);

        private static class Windows
        {
            private const string Library = "winsqlite3.dll";

            [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
            [DllImport(Library, CallingConvention = CallingConvention.StdCall, ExactSpelling = true)]
            internal static extern int sqlite3_open_v2(byte[] filename, out IntPtr database, int flags, IntPtr vfs);

            [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
            [DllImport(Library, CallingConvention = CallingConvention.StdCall, ExactSpelling = true)]
            internal static extern int sqlite3_busy_timeout(IntPtr database, int milliseconds);

            [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
            [DllImport(Library, CallingConvention = CallingConvention.StdCall, ExactSpelling = true)]
            internal static extern int sqlite3_exec(IntPtr database, byte[] sql, WindowsRowCallback callback, IntPtr context, out IntPtr error);

            [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
            [DllImport(Library, CallingConvention = CallingConvention.StdCall, ExactSpelling = true)]
            internal static extern void sqlite3_free(IntPtr pointer);

            [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
            [DllImport(Library, CallingConvention = CallingConvention.StdCall, ExactSpelling = true)]
            internal static extern int sqlite3_close_v2(IntPtr database);
        }

        private static class Mac
        {
            private const string Library = "/usr/lib/libsqlite3.dylib";

            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
            internal static extern int sqlite3_open_v2(byte[] filename, out IntPtr database, int flags, IntPtr vfs);

            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
            internal static extern int sqlite3_busy_timeout(IntPtr database, int milliseconds);

            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
            internal static extern int sqlite3_exec(IntPtr database, byte[] sql, MacRowCallback callback, IntPtr context, out IntPtr error);

            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
            internal static extern void sqlite3_free(IntPtr pointer);

            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
            internal static extern int sqlite3_close_v2(IntPtr database);
        }

        public NativeSqlite(string path, bool create, bool useWindows)
        {
            windows = useWindows;
            byte[] filename = Utf8(path);
            int flags = OpenReadWrite | (create ? OpenCreate : 0);
            try
            {
                int result = windows
                    ? Windows.sqlite3_open_v2(filename, out database, flags, IntPtr.Zero)
                    : Mac.sqlite3_open_v2(filename, out database, flags, IntPtr.Zero);
                Check(result, "open");
                Check(windows
                    ? Windows.sqlite3_busy_timeout(database, 10000)
                    : Mac.sqlite3_busy_timeout(database, 10000), "busy timeout");
            }
            catch
            {
                Dispose();
                throw;
            }
        }

        private static byte[] Utf8(string text)
        {
            if (text == null || text.IndexOf('\0') >= 0)
                throw new InvalidOperationException("Invalid native SQLite input.");
            return new UTF8Encoding(false, true).GetBytes(text + "\0");
        }

        private static void Check(int result, string operation)
        {
            // Native error strings may contain paths or SQL; expose only the numeric result.
            if (result != 0)
                throw new InvalidOperationException("SQLite " + operation + " failed (code " +
                    result.ToString(CultureInfo.InvariantCulture) + ").");
        }

        private static string SafeField(IntPtr pointer)
        {
            if (pointer == IntPtr.Zero)
                return String.Empty;
            StringBuilder field = new StringBuilder();
            for (int index = 0; index < 4096; index++)
            {
                byte value = Marshal.ReadByte(pointer, index);
                if (value == 0)
                    return field.ToString();
                if (!((value >= 'a' && value <= 'z') ||
                      (value >= 'A' && value <= 'Z') ||
                      (value >= '0' && value <= '9') ||
                      value == '_' || value == '-' || value == '.' || value == ':'))
                    throw new InvalidOperationException("Unsafe SQLite output.");
                field.Append((char)value);
            }
            throw new InvalidOperationException("Oversized SQLite output.");
        }

        public string[] Execute(string sql)
        {
            if (database == IntPtr.Zero)
                throw new ObjectDisposedException("NativeSqlite");
            List<string> rows = new List<string>();
            bool callbackFailed = false;
            Func<IntPtr, int, IntPtr, IntPtr, int> collect = delegate(IntPtr context, int count, IntPtr values, IntPtr names)
            {
                try
                {
                    if (count < 1 || count > 64)
                        throw new InvalidOperationException("Invalid SQLite output.");
                    string[] fields = new string[count];
                    for (int index = 0; index < count; index++)
                        fields[index] = SafeField(Marshal.ReadIntPtr(values, index * IntPtr.Size));
                    rows.Add(String.Join("|", fields));
                    return 0;
                }
                catch
                {
                    // Exceptions must not cross the unmanaged callback boundary.
                    callbackFailed = true;
                    return 1;
                }
            };
            WindowsRowCallback windowsCallback = windows ? new WindowsRowCallback(collect.Invoke) : null;
            MacRowCallback macCallback = windows ? null : new MacRowCallback(collect.Invoke);
            IntPtr error = IntPtr.Zero;
            try
            {
                byte[] statement = Utf8(sql);
                int result = windows
                    ? Windows.sqlite3_exec(database, statement, windowsCallback, IntPtr.Zero, out error)
                    : Mac.sqlite3_exec(database, statement, macCallback, IntPtr.Zero, out error);
                if (callbackFailed)
                    throw new InvalidOperationException("SQLite returned unsafe output.");
                Check(result, "execution");
                return rows.ToArray();
            }
            finally
            {
                if (error != IntPtr.Zero)
                {
                    if (windows) Windows.sqlite3_free(error);
                    else Mac.sqlite3_free(error);
                }
                GC.KeepAlive(windowsCallback);
                GC.KeepAlive(macCallback);
            }
        }

        public void Dispose()
        {
            if (database == IntPtr.Zero)
                return;
            IntPtr handle = database;
            database = IntPtr.Zero;
            Check(windows ? Windows.sqlite3_close_v2(handle) : Mac.sqlite3_close_v2(handle), "close");
        }
    }
}
````

Resource: scripts/schema.sql
SHA-256: 8a3eb43d481bc791cbbefb9e00d0e9a2a2d18282c66536db414ad9321cea6efb
````text
BEGIN IMMEDIATE;
CREATE TEMP TABLE schema_assertion (valid INTEGER NOT NULL CHECK (valid = 1));
INSERT INTO schema_assertion
SELECT CASE
  WHEN (SELECT application_id FROM pragma_application_id) = 0
   AND (SELECT user_version FROM pragma_user_version) = 0
   AND NOT EXISTS (SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%')
    THEN 1
  WHEN (SELECT application_id FROM pragma_application_id) = 1095783252
   AND (SELECT user_version FROM pragma_user_version) = 1
   AND (SELECT count(*) FROM sqlite_master
        WHERE type = 'table' AND name IN ('requests', 'run_lock')) = 2
    THEN 1
  ELSE 0 END;
INSERT INTO schema_assertion
SELECT CASE WHEN (SELECT quick_check FROM pragma_quick_check LIMIT 1) = 'ok'
  THEN 1 ELSE 0 END;
CREATE TABLE IF NOT EXISTS run_lock (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  owner TEXT NOT NULL CHECK (length(owner) = 32),
  expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS requests (
  message_hash TEXT PRIMARY KEY NOT NULL CHECK (length(message_hash) = 64),
  reference TEXT NOT NULL UNIQUE DEFAULT (lower(hex(randomblob(16)))),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked', 'completed')),
  estimate_state TEXT NOT NULL DEFAULT 'pending' CHECK (estimate_state IN ('pending', 'started', 'done')),
  draft_state TEXT NOT NULL DEFAULT 'pending' CHECK (draft_state IN ('pending', 'started', 'done')),
  teams_state TEXT NOT NULL DEFAULT 'pending' CHECK (teams_state IN ('pending', 'started', 'done')),
  estimate_receipt TEXT NOT NULL DEFAULT '',
  draft_receipt TEXT NOT NULL DEFAULT '',
  teams_receipt TEXT NOT NULL DEFAULT '',
  reason TEXT NOT NULL DEFAULT '',
  updated_at INTEGER NOT NULL,
  CHECK (draft_state = 'pending' OR estimate_state = 'done'),
  CHECK (teams_state = 'pending' OR draft_state = 'done'),
  CHECK (status <> 'completed' OR
    (estimate_state = 'done' AND draft_state = 'done' AND teams_state = 'done')),
  CHECK ((estimate_state = 'done') = (length(estimate_receipt) = 64)),
  CHECK ((draft_state = 'done') = (length(draft_receipt) = 64)),
  CHECK ((teams_state = 'done') = (length(teams_receipt) = 64))
);
-- The adapter's extension marker distinguishes a legacy database from lost checkpoints.
INSERT INTO schema_assertion
SELECT CASE WHEN __ARTIFACTS_REQUIRED__ = 0 OR EXISTS (
  SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'estimate_artifacts'
) THEN 1 ELSE 0 END;
INSERT INTO schema_assertion
SELECT CASE WHEN EXISTS (
  SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'estimate_artifacts'
) OR NOT EXISTS (
  SELECT 1 FROM run_lock WHERE expires_at > CAST(strftime('%s', 'now') AS INTEGER)
    AND owner <> '__OWNER__'
) THEN 1 ELSE 0 END;
CREATE TABLE IF NOT EXISTS estimate_artifacts (
  message_hash TEXT NOT NULL REFERENCES requests(message_hash),
  source_hash TEXT NOT NULL CHECK (length(source_hash) = 64 AND source_hash NOT GLOB '*[^0-9a-f]*'
    AND instr(source_hash, char(0)) = 0),
  state TEXT NOT NULL CHECK (state IN ('started', 'done')),
  intent_hash TEXT NOT NULL CHECK (length(intent_hash) = 64 AND intent_hash NOT GLOB '*[^0-9a-f]*'
    AND instr(intent_hash, char(0)) = 0),
  saved_id_hash TEXT NOT NULL DEFAULT '',
  updated_at INTEGER NOT NULL CHECK (typeof(updated_at) = 'integer' AND updated_at >= 0),
  PRIMARY KEY (message_hash, source_hash),
  CHECK ((state = 'started' AND saved_id_hash = '') OR
    (state = 'done' AND length(saved_id_hash) = 64 AND saved_id_hash NOT GLOB '*[^0-9a-f]*'
      AND instr(saved_id_hash, char(0)) = 0))
);
CREATE UNIQUE INDEX IF NOT EXISTS estimate_artifacts_saved_id
  ON estimate_artifacts (saved_id_hash) WHERE state = 'done';
PRAGMA application_id = 1095783252;
PRAGMA user_version = 1;
DROP TABLE schema_assertion;
COMMIT;
````

Resource: scripts/tracker.sql
SHA-256: 351a504139e221ee9bc46cf40cda1af9b423e860c97084ade53687653e550b6a
````text
BEGIN IMMEDIATE;
CREATE TEMP TABLE input AS SELECT
  '__ACTION__' AS action, '__MESSAGE__' AS message, '__OWNER__' AS owner,
  '__STAGE__' AS stage, '__RECEIPT__' AS receipt, '__REASON__' AS reason,
  '__SOURCE__' AS source,
  CAST(strftime('%s', 'now') AS INTEGER) AS now;
CREATE TEMP TABLE operation_assertion (valid INTEGER NOT NULL CHECK (valid = 1));
INSERT INTO operation_assertion
SELECT CASE WHEN (SELECT application_id FROM pragma_application_id) = 1095783252
  AND (SELECT user_version FROM pragma_user_version) = 1
  AND EXISTS (SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'estimate_artifacts')
  AND EXISTS (SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = 'estimate_artifacts_saved_id')
  THEN 1 ELSE 0 END;
INSERT INTO operation_assertion
SELECT CASE WHEN action IN ('init', 'acquire', 'release', 'status')
  OR EXISTS (SELECT 1 FROM run_lock WHERE singleton = 1
    AND owner = input.owner AND expires_at > input.now)
  THEN 1 ELSE 0 END FROM input;

INSERT OR IGNORE INTO run_lock
SELECT 1, owner, now + 900 FROM input WHERE action = 'acquire';
UPDATE run_lock SET
  owner = (SELECT owner FROM input),
  expires_at = (SELECT now + 900 FROM input)
WHERE (SELECT action FROM input) = 'acquire'
  AND (expires_at <= (SELECT now FROM input) OR owner = (SELECT owner FROM input));
UPDATE run_lock SET expires_at = (SELECT now + 900 FROM input)
WHERE (SELECT action FROM input) = 'heartbeat' AND owner = (SELECT owner FROM input);
DELETE FROM run_lock WHERE (SELECT action FROM input) = 'release'
  AND owner = (SELECT owner FROM input);

INSERT OR IGNORE INTO requests (message_hash, updated_at)
SELECT message, now FROM input WHERE action = 'claim';
INSERT INTO operation_assertion
SELECT CASE WHEN EXISTS (SELECT 1 FROM requests WHERE message_hash = input.message)
  THEN 1 ELSE 0 END FROM input
WHERE action IN ('begin', 'confirm', 'retry-stage', 'block', 'retry', 'complete',
  'artifact-begin', 'artifact-status', 'artifact-confirm', 'artifact-list');
INSERT INTO operation_assertion
SELECT CASE WHEN EXISTS (SELECT 1 FROM requests
  WHERE message_hash = input.message AND status = 'active'
  AND CASE input.stage
    WHEN 'estimate' THEN estimate_state
    WHEN 'draft' THEN draft_state
    WHEN 'teams' THEN teams_state END =
      CASE input.action WHEN 'begin' THEN 'pending' ELSE 'started' END
  AND (input.stage = 'estimate' OR estimate_state = 'done')
  AND (input.stage <> 'teams' OR draft_state = 'done'))
  THEN 1 ELSE 0 END FROM input WHERE action IN ('begin', 'confirm', 'retry-stage');
INSERT INTO operation_assertion
SELECT CASE WHEN length(receipt) = 64 THEN 1 ELSE 0 END FROM input WHERE action = 'confirm';
INSERT INTO operation_assertion
SELECT CASE WHEN EXISTS (SELECT 1 FROM requests WHERE message_hash = input.message
  AND status <> 'completed') THEN 1 ELSE 0 END FROM input WHERE action IN ('block', 'retry');
INSERT INTO operation_assertion
SELECT CASE WHEN EXISTS (SELECT 1 FROM requests WHERE message_hash = input.message
  AND status IN ('active', 'completed') AND estimate_state = 'done'
  AND draft_state = 'done' AND teams_state = 'done') THEN 1 ELSE 0 END
FROM input WHERE action = 'complete';

-- Check all sources before reading or changing checkpoints; never hide a malformed row.
INSERT INTO operation_assertion
SELECT CASE WHEN NOT EXISTS (
  SELECT 1 FROM estimate_artifacts WHERE message_hash = input.message AND NOT COALESCE(
    typeof(source_hash) = 'text' AND length(source_hash) = 64
    AND source_hash NOT GLOB '*[^0-9a-f]*' AND instr(source_hash, char(0)) = 0
    AND typeof(intent_hash) = 'text' AND length(intent_hash) = 64
    AND intent_hash NOT GLOB '*[^0-9a-f]*' AND instr(intent_hash, char(0)) = 0
    AND typeof(saved_id_hash) = 'text'
    AND ((state = 'started' AND saved_id_hash = '') OR
      (state = 'done' AND length(saved_id_hash) = 64
        AND saved_id_hash NOT GLOB '*[^0-9a-f]*' AND instr(saved_id_hash, char(0)) = 0))
    AND typeof(updated_at) = 'integer' AND updated_at >= 0, 0)
) THEN 1 ELSE 0 END FROM input
WHERE action IN ('artifact-begin', 'artifact-status', 'artifact-confirm', 'artifact-list')
  OR (action = 'confirm' AND stage = 'estimate');
INSERT INTO operation_assertion
SELECT CASE WHEN EXISTS (
  SELECT 1 FROM requests WHERE message_hash = input.message
    AND status = 'active' AND estimate_state = 'started'
) AND length(source) = 64 AND length(receipt) = 64 THEN 1 ELSE 0 END
FROM input WHERE action IN ('artifact-begin', 'artifact-confirm');
INSERT INTO operation_assertion
SELECT CASE WHEN NOT EXISTS (
  SELECT 1 FROM estimate_artifacts WHERE message_hash = input.message
    AND source_hash = input.source AND intent_hash <> input.receipt
) THEN 1 ELSE 0 END FROM input WHERE action = 'artifact-begin';
INSERT INTO estimate_artifacts (message_hash, source_hash, state, intent_hash, updated_at)
SELECT message, source, 'started', receipt, now FROM input WHERE action = 'artifact-begin'
  AND NOT EXISTS (SELECT 1 FROM estimate_artifacts
    WHERE message_hash = input.message AND source_hash = input.source);
INSERT INTO operation_assertion
SELECT CASE WHEN EXISTS (
  SELECT 1 FROM estimate_artifacts WHERE message_hash = input.message AND source_hash = input.source
    AND (state = 'started' OR (state = 'done' AND saved_id_hash = input.receipt))
) AND NOT EXISTS (
  SELECT 1 FROM estimate_artifacts WHERE saved_id_hash = input.receipt
    AND (message_hash <> input.message OR source_hash <> input.source)
) THEN 1 ELSE 0 END FROM input WHERE action = 'artifact-confirm';
UPDATE estimate_artifacts SET state = 'done', saved_id_hash = (SELECT receipt FROM input),
  updated_at = (SELECT now FROM input)
WHERE (SELECT action FROM input) = 'artifact-confirm' AND state = 'started'
  AND message_hash = (SELECT message FROM input) AND source_hash = (SELECT source FROM input);
INSERT INTO operation_assertion
SELECT CASE WHEN NOT EXISTS (
  SELECT 1 FROM estimate_artifacts WHERE message_hash = input.message AND state <> 'done'
) THEN 1 ELSE 0 END FROM input WHERE action = 'confirm' AND stage = 'estimate';

UPDATE requests SET
  estimate_state = CASE WHEN (SELECT stage FROM input) = 'estimate'
    THEN CASE (SELECT action FROM input) WHEN 'begin' THEN 'started'
      WHEN 'confirm' THEN 'done' ELSE 'pending' END ELSE estimate_state END,
  draft_state = CASE WHEN (SELECT stage FROM input) = 'draft'
    THEN CASE (SELECT action FROM input) WHEN 'begin' THEN 'started'
      WHEN 'confirm' THEN 'done' ELSE 'pending' END ELSE draft_state END,
  teams_state = CASE WHEN (SELECT stage FROM input) = 'teams'
    THEN CASE (SELECT action FROM input) WHEN 'begin' THEN 'started'
      WHEN 'confirm' THEN 'done' ELSE 'pending' END ELSE teams_state END,
  estimate_receipt = CASE WHEN (SELECT stage FROM input) = 'estimate'
      AND (SELECT action FROM input) = 'confirm'
    THEN (SELECT receipt FROM input) ELSE estimate_receipt END,
  draft_receipt = CASE WHEN (SELECT stage FROM input) = 'draft'
      AND (SELECT action FROM input) = 'confirm'
    THEN (SELECT receipt FROM input) ELSE draft_receipt END,
  teams_receipt = CASE WHEN (SELECT stage FROM input) = 'teams'
      AND (SELECT action FROM input) = 'confirm'
    THEN (SELECT receipt FROM input) ELSE teams_receipt END,
  updated_at = (SELECT now FROM input)
WHERE message_hash = (SELECT message FROM input)
  AND (SELECT action FROM input) IN ('begin', 'confirm', 'retry-stage');
UPDATE requests SET
  status = CASE (SELECT action FROM input)
    WHEN 'block' THEN 'blocked' WHEN 'retry' THEN 'active' ELSE 'completed' END,
  reason = CASE (SELECT action FROM input) WHEN 'block' THEN (SELECT reason FROM input) ELSE '' END,
  updated_at = (SELECT now FROM input)
WHERE message_hash = (SELECT message FROM input)
  AND (SELECT action FROM input) IN ('block', 'retry', 'complete');

SELECT 'init', 1, lower(hex(randomblob(16))) FROM input WHERE action = 'init';
SELECT CASE WHEN EXISTS (SELECT 1 FROM run_lock WHERE owner = input.owner
  AND expires_at > input.now) THEN 'acquired' ELSE 'busy' END,
  (SELECT expires_at FROM run_lock WHERE singleton = 1)
FROM input WHERE action = 'acquire';
SELECT 'heartbeat', (SELECT expires_at FROM run_lock WHERE singleton = 1)
FROM input WHERE action = 'heartbeat';
SELECT 'released' FROM input WHERE action = 'release';
SELECT CASE WHEN status = 'completed' THEN 'skip_completed'
    WHEN status = 'blocked' THEN 'skip_blocked'
    WHEN 'started' IN (estimate_state, draft_state, teams_state) THEN 'reconcile'
    ELSE 'ready' END,
  reference, status, estimate_state, draft_state, teams_state,
  estimate_receipt, draft_receipt, teams_receipt, reason
FROM requests WHERE message_hash = (SELECT message FROM input)
  AND (SELECT action FROM input) IN ('claim', 'status', 'begin', 'confirm',
    'retry-stage', 'block', 'retry', 'complete');
SELECT 'not_found' FROM input WHERE action = 'status'
  AND NOT EXISTS (SELECT 1 FROM requests WHERE message_hash = input.message);
-- Validate persisted fields before either adapter exposes any listing rows.
INSERT INTO operation_assertion
SELECT CASE WHEN NOT EXISTS (
  SELECT 1 FROM requests WHERE status IN ('active', 'blocked') AND NOT (
    length(reference) = 32 AND reference NOT GLOB '*[^0-9a-f]*'
    AND instr(reference, char(0)) = 0
    AND estimate_state IN ('pending', 'started', 'done')
    AND draft_state IN ('pending', 'started', 'done')
    AND teams_state IN ('pending', 'started', 'done')
    AND reason IN ('', 'unreadable_requirements', 'permission_restriction',
      'ambiguous_recipient', 'uncertain_outcome', 'delivery_failed', 'other')
    AND typeof(updated_at) = 'integer' AND updated_at >= 0
  )) THEN 1 ELSE 0 END FROM input WHERE action = 'list-open';
SELECT reference, status, estimate_state, draft_state, teams_state, reason, updated_at
FROM requests WHERE status IN ('active', 'blocked')
  AND (SELECT action FROM input) = 'list-open'
ORDER BY updated_at, reference;
SELECT source_hash, state, intent_hash, saved_id_hash, updated_at
FROM estimate_artifacts WHERE message_hash = (SELECT message FROM input)
  AND ((SELECT action FROM input) = 'artifact-list' OR
    ((SELECT action FROM input) IN ('artifact-begin', 'artifact-status', 'artifact-confirm')
      AND source_hash = (SELECT source FROM input)))
ORDER BY source_hash;
SELECT 'not_found' FROM input WHERE action = 'artifact-status'
  AND NOT EXISTS (SELECT 1 FROM estimate_artifacts
    WHERE message_hash = input.message AND source_hash = input.source);
COMMIT;
````

