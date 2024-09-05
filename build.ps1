# Check if .venv folder exists
if (-not (Test-Path "./.venv")) {
  Write-Output "Warning: .venv folder not found. Please check the README for setup instructions."
  exit 1
}

# Import Activate.ps1 based on the operating system
if ($IsLinux) {
  & "./.venv/bin/Activate.ps1"
} elseif ($IsWindows) {
  & "./.venv/Scripts/Activate.ps1"
}

# Set up output folder
Write-Output "Copying source files to the build folder..."
$srcPath = Join-Path $PSScriptRoot "src"
$svgPath = Join-Path $PSScriptRoot "svg"
$outPath = Join-Path $PSScriptRoot "deorder-plugins"
$buildPath = Join-Path $PSScriptRoot "build"
if (-not (Test-Path $outPath)) {
  New-Item -ItemType Directory -Path $outPath | Out-Null
}
  
# Copy all .py files and LICENSE to the build folder
Copy-Item -Path "$srcPath/*.py" -Destination $outPath -Recurse -Force -Exclude "resources.py"
Copy-Item -Path "LICENSE" -Destination $outPath -Force
Write-Output "Source files copied successfully"

# Run scour on all svg files
Write-Output "Setting up resources..."
if (Test-Path $buildPath) {
  Remove-Item -Path $buildPath -Recurse -Force
}
New-Item -ItemType Directory -Path $buildPath | Out-Null
Copy-Item -Path "$srcPath/resources.qrc" -Destination $buildPath -Force
$svgFiles = Get-ChildItem -Path $svgPath -Filter "*.svg" -Recurse
foreach ($file in $svgFiles) {
  & "scour" -i "svg/$($file.Name)" -o "$buildPath/$($file.Name)" --enable-id-stripping --enable-comment-stripping --shorten-ids --indent=none
  if ($LASTEXITCODE -ne 0) {
    throw "scour execution for $($file.Name) failed with exit code: $LASTEXITCODE"
  }
}
Write-Output "Resources ready for packaging"

# Run rcc.exe with the specified parameters
Write-Output "Running rcc..."
& "pyside6-rcc" -g python -compress 2 -threshold 30 "$buildPath/resources.qrc" -o "$outPath/resources.py"
if ($LASTEXITCODE -ne 0) {
  throw "rcc execution failed with exit code: $LASTEXITCODE"
}
Remove-Item -Path $buildPath -Recurse -Force
Write-Output "rcc executed successfully"

# Replace PySide6 with PyQt6 in the generated file
Write-Output "Replacing PySide6 with PyQt6 in resources.py (if necessary)..."
$content = Get-Content $outPath/resources.py -Raw
$newContent = $content -replace 'from PySide6 import QtCore', 'from PyQt6 import QtCore'
if ($newContent -eq $content) {
  Write-Output "No replacements were made or necessary"
}
else {
  $newContent | Set-Content $outPath/resources.py
  Write-Output "Replacement completed successfully"
}

Write-Output "Script completed successfully"