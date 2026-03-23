Param(
    [string]$Name = "PodongApp",
    [string]$Icon = "",
    [switch]$OneFile,
    [switch]$Windowed,
    [switch]$Debug
)

# Defaults suitable for a GUI Flet app
if (-not $OneFile) { $OneFile = $true }
if (-not $Windowed) { $Windowed = $true }

Write-Host "==> Packaging Flet app to single EXE..." -ForegroundColor Cyan

# Ensure flet CLI is available
try {
    $null = & flet --version
} catch {
    Write-Error "'flet' CLI not found. Activate your venv and run: pip install 'flet[all]' pyinstaller"
    exit 1
}

if (-not (Test-Path "main.py")) {
    Write-Error "main.py not found in current directory. Run this script from the project root."
    exit 1
}

$argsList = @("pack", ".\main.py", "--name", $Name)
if ($OneFile) { $argsList += "--onefile" }
if ($Windowed) { $argsList += "--windowed" }
if ($Debug) { $argsList += @("--log-level", "DEBUG") }
if ($Icon -and (Test-Path $Icon)) { $argsList += @("--icon", $Icon) }

# Add common data files/folders if they exist
if (Test-Path "exception_list.json") { $argsList += @("--add-data", "exception_list.json;.") }
if (Test-Path "src\ui") { $argsList += @("--add-data", "src\ui;src\ui") }

Write-Host ("flet " + ($argsList -join ' ')) -ForegroundColor DarkCyan

# Invoke builder
& flet @argsList

if ($LASTEXITCODE -ne 0) {
    Write-Error "Packaging failed (exit code $LASTEXITCODE). Check the log output above."
    exit $LASTEXITCODE
}

Write-Host "==> Done. Find your EXE under .\dist\$Name.exe" -ForegroundColor Green

