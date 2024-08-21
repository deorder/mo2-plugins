try {
  # Find the latest Qt version
  Write-Output "Searching for the latest Qt version..."
  $qtPath = "C:\Qt"
  $allVersions = Get-ChildItem $qtPath | Where-Object {
    $_.Name -match '^\d+(\.\d+)*$'
  } | Sort-Object { [version]$_.Name } -Descending
    
  $latestVersion = $allVersions | Select-Object -First 1
  if (-not $latestVersion) {
    throw "No valid Qt versions found in $qtPath"
  }
  Write-Output "Latest Qt version found: $($latestVersion.Name)"

  # Find a platform folder (e.g., msvc2019_64, msvc2022_64, mingw_64, etc.)
  Write-Output "Searching for a platform folder..."
  $platformPath = $latestVersion.FullName
  $platform = (Get-ChildItem $platformPath | Where-Object { $_.PSIsContainer } | Sort-Object Name -Descending | Select-Object -First 1).Name
  if (-not $platform) {
    throw "No platform folders found in $platformPath"
  }
  Write-Output "Platform folder found: $platform"

  # Construct the full path to rcc.exe
  Write-Output "Constructing path to rcc.exe..."
  $rccPath = Join-Path $platformPath $platform "bin\rcc.exe"
  if (-not (Test-Path $rccPath)) {
    throw "rcc.exe not found at path: $rccPath"
  }
  Write-Output "rcc.exe path: $rccPath"

  # Run rcc.exe with the specified parameters
  Write-Output "Running rcc.exe..."
  & $rccPath -g python -compress 2 -threshold 30 resources.qrc -o resources.py
  if ($LASTEXITCODE -ne 0) {
    throw "rcc.exe execution failed with exit code: $LASTEXITCODE"
  }
  Write-Output "rcc.exe executed successfully"

  # Replace PySide6 with PyQt6 in the generated file
  Write-Output "Replacing PySide6 with PyQt6 in resources.py (if necessary)..."
  $content = Get-Content resources.py -Raw
  $newContent = $content -replace 'from PySide6 import QtCore', 'from PyQt6 import QtCore'
  if ($newContent -eq $content) {
    Write-Output "No replacements were made or necessary"
  }
  else {
    $newContent | Set-Content resources.py
    Write-Output "Replacement completed successfully"
  }

  Write-Output "Script completed successfully"
}
catch {
  Write-Output "Error: $_"
  exit 1
}