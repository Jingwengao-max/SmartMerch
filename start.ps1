param(
    [switch]$Quick
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$venvDir = Join-Path $PSScriptRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$envFile = Join-Path $PSScriptRoot ".env"

function Test-CompatiblePython {
    param([Parameter(Mandatory = $true)][string]$Executable)

    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        return $false
    }
    try {
        $version = & $Executable -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        $match = [regex]::Match([string]$version, '^3\.(\d+)$')
        return $LASTEXITCODE -eq 0 -and $match.Success -and
            [int]$match.Groups[1].Value -ge 11 -and
            [int]$match.Groups[1].Value -le 14
    } catch {
        return $false
    }
}

function Find-CompatiblePython {
    $candidates = [System.Collections.Generic.List[string]]::new()

    $pyCommands = @(Get-Command py -All -ErrorAction SilentlyContinue)
    foreach ($pyCommand in $pyCommands) {
        if (-not $pyCommand.Source) { continue }
        foreach ($selector in @("-3.14", "-3.13", "-3.12", "-3.11")) {
            try {
                $version = & $pyCommand.Source $selector -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                if ($LASTEXITCODE -eq 0 -and $version -in @("3.11", "3.12", "3.13", "3.14")) {
                    return [PSCustomObject]@{
                        Executable = $pyCommand.Source
                        PrefixArguments = @($selector)
                    }
                }
            } catch {
                continue
            }
        }
    }

    if ($env:SMARTMERCH_PYTHON) {
        $candidates.Add($env:SMARTMERCH_PYTHON)
    }

    foreach ($pattern in @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.14-*\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.13-*\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.12-*\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.11-*\python.exe"),
        (Join-Path $env:ProgramFiles "Python314\python.exe"),
        (Join-Path $env:ProgramFiles "Python313\python.exe"),
        (Join-Path $env:ProgramFiles "Python312\python.exe"),
        (Join-Path $env:ProgramFiles "Python311\python.exe")
    )) {
        Get-Item -Path $pattern -ErrorAction SilentlyContinue | ForEach-Object {
            $candidates.Add($_.FullName)
        }
    }

    foreach ($commandName in @("python", "python3")) {
        Get-Command $commandName -All -ErrorAction SilentlyContinue | ForEach-Object {
            if ($_.Source) { $candidates.Add($_.Source) }
        }
    }

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (Test-CompatiblePython -Executable $candidate) {
            return [PSCustomObject]@{
                Executable = $candidate
                PrefixArguments = @()
            }
        }
    }

    throw "Python 3.11 to 3.14 was not found. Install Python 3.12 from https://www.python.org/downloads/windows/ and enable Add Python to PATH, then run start-smartmerch.cmd again. For a custom location, set SMARTMERCH_PYTHON to the full path of python.exe."
}

function Assert-NodeEnvironment {
    $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
    $npmCommand = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $nodeCommand -or -not $npmCommand) {
        throw "Node.js/npm was not found. Install Node.js 20 or newer from https://nodejs.org/ and try again."
    }

    $major = [int]((& node -p "process.versions.node.split('.')[0]").Trim())
    if ($major -lt 20) {
        throw "Detected Node.js major version $major. SmartMerch requires Node.js 20 or newer."
    }
}

function Read-ApiKey {
    param([Parameter(Mandatory = $true)][string]$Prompt)

    while ($true) {
        Write-Host $Prompt -ForegroundColor Cyan
        Read-Host "Copy the API key in your browser, then press Enter here to read it from the clipboard"
        try {
            $key = ((Get-Clipboard) -join "").Trim()
        } catch {
            throw "The clipboard could not be read. Set the API variables manually as documented in README.md."
        }
        if ($key.Length -ge 10 -and $key -notmatch '[\x00-\x1F\x7F]') {
            try { Set-Clipboard -Value "" } catch { }
            return $key
        }
        Write-Host "No valid API key was found in the clipboard. Copy the complete key and try again." -ForegroundColor Yellow
    }
}

function Invoke-FirstRunWizard {
    if (Test-Path -LiteralPath $envFile) {
        return
    }

    Write-Host ""
    Write-Host "First-run setup" -ForegroundColor Cyan
    Write-Host "AI translation and copy suggestions are optional. Core editing and export work without them."
    $configureAi = Read-Host "Configure AI services now? [y/N]"
    if ($configureAi -notmatch '^(y|yes)$') {
        @(
            "# SmartMerch local configuration. This file is ignored by Git.",
            "# To enable AI later, add the variables documented in README.md."
        ) | Set-Content -LiteralPath $envFile -Encoding utf8
        return
    }

    Write-Host "Vision provider: [1] Qianwen pay-as-you-go  [2] Qianwen Token Plan  [3] Custom"
    $visionProvider = Read-Host "Choose a provider (press Enter for 1)"
    switch ($visionProvider) {
        "2" {
            $visionUrl = "https://token-plan.maas.qianwenaiapi.com/compatible-mode/v1"
            $visionModel = "qwen3-vl-plus"
        }
        "3" {
            $visionUrl = Read-Host "Vision model Base URL"
            $visionModel = Read-Host "Vision model name"
        }
        default {
            $visionUrl = "https://maas.qianwenaiapi.com/compatible-mode/v1"
            $visionModel = "qwen3-vl-plus"
        }
    }
    $visionKey = Read-ApiKey "Vision model API Key"

    @(
        "# SmartMerch local configuration. This file is ignored by Git.",
        "AI_API_URL=$visionUrl",
        "AI_API_KEY=$visionKey",
        "AI_MODEL=$visionModel"
    ) | Set-Content -LiteralPath $envFile -Encoding utf8
    Write-Host "AI configuration was saved to the local .env file." -ForegroundColor Green
}

function Import-DotEnv {
    if (-not (Test-Path -LiteralPath $envFile)) {
        return
    }

    foreach ($line in Get-Content -LiteralPath $envFile) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }
        $name, $value = $trimmed.Split("=", 2)
        $name = $name.Trim()
        if ($name -match '^[A-Za-z_][A-Za-z0-9_]*$') {
            [Environment]::SetEnvironmentVariable($name, $value.Trim().Trim('"').Trim("'"), "Process")
        }
    }
}

if ($Quick) {
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        throw "First-time setup is incomplete. Run start-smartmerch.cmd first."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot "dist\index.html") -PathType Leaf)) {
        throw "The frontend has not been built. Run start-smartmerch.cmd first."
    }
} else {
    Assert-NodeEnvironment

    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        $systemPython = Find-CompatiblePython
        Write-Host "[1/4] Creating the Python virtual environment..." -ForegroundColor Cyan
        $pythonArguments = @($systemPython.PrefixArguments) + @("-m", "venv", $venvDir)
        & $systemPython.Executable @pythonArguments
        if ($LASTEXITCODE -ne 0) { throw "Failed to create the Python virtual environment." }
    } else {
        Write-Host "[1/4] Using the existing Python virtual environment." -ForegroundColor Cyan
    }

    Write-Host "[2/4] Installing backend dependencies..." -ForegroundColor Cyan
    & $venvPython -m pip install --disable-pip-version-check -r backend\requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Failed to install backend dependencies." }

    Write-Host "[3/4] Installing and building the frontend..." -ForegroundColor Cyan
    $nodeModulesDir = Join-Path $PSScriptRoot "node_modules"
    $npmStateFile = Join-Path $nodeModulesDir ".package-lock.json"
    $packageLockFile = Join-Path $PSScriptRoot "package-lock.json"
    $packageFile = Join-Path $PSScriptRoot "package.json"
    $needsNpmInstall = -not (Test-Path -LiteralPath $nodeModulesDir -PathType Container) -or
        -not (Test-Path -LiteralPath $npmStateFile -PathType Leaf)
    if (-not $needsNpmInstall) {
        $npmStateTime = (Get-Item -LiteralPath $npmStateFile).LastWriteTimeUtc
        $needsNpmInstall = (Get-Item -LiteralPath $packageLockFile).LastWriteTimeUtc -gt $npmStateTime -or
            (Get-Item -LiteralPath $packageFile).LastWriteTimeUtc -gt $npmStateTime
    }
    if ($needsNpmInstall) {
        & npm ci
        if ($LASTEXITCODE -ne 0) { throw "Failed to install frontend dependencies." }
    } else {
        Write-Host "Frontend dependencies are up to date." -ForegroundColor DarkGray
    }
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw "Failed to build the frontend." }

    Write-Host "[4/4] Completing first-run configuration..." -ForegroundColor Cyan
    Invoke-FirstRunWizard
}

Import-DotEnv
Write-Host "Starting SmartMerch. The browser will open automatically; close this window to stop the server." -ForegroundColor Green
Set-Location -LiteralPath (Join-Path $PSScriptRoot "backend")
& $venvPython api.py
if ($LASTEXITCODE -ne 0) { throw "The SmartMerch backend exited with an error." }
