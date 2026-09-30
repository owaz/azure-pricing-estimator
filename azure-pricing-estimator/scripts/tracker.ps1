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
