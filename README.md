# Mod Organizer 2 Plugins

## Description

This repository contains two Mod Organizer 2 plugins:

1. **Merge Plugins Hide**: Allows hiding or unhiding plugins that were merged using `Merge Plugins` or `zMerge`.
2. **Sync Mod Order**: Synchronizes mod order from the current profile to another while preserving the enabled/disabled state of mods.

## Installation

1. Download the latest `.zip` file from the [Releases](https://github.com/your-repo/releases) page.
2. Extract the contents into Mod Organizer 2's `plugins/` folder.
3. Rename the extracted folder to avoid potential errors (e.g., `deorder`).
4. The plugins will appear in the `Tools` menu (puzzle piece icon) within Mod Organizer 2.

## Merge Plugins Hide

This plugin offers flexibility in managing merged plugins.

### Hide Methods
Configure the hiding method by changing the `hide-type` setting:

1. **mohidden**: Hides plugins using MO2's virtual file system by appending `.mohidden` to the plugin file.
2. **optional**: Hides plugins by moving them to an `optional` directory within the mod.
3. **disable**: Hides plugins by disabling them (compatible with zMerge's method).

## Sync Mod Order

This plugin allows you to synchronize mod orders between profiles while maintaining the enabled/disabled states of individual mods.

## Build Instructions

### Prerequisites
- Python 3.12 or newer
- Qt 6.x or newer (installed in `C:\Qt`)

### First-Time Setup
1. Install Qt from: https://www.qt.io/download-qt-installer
   Make sure to install it in `C:\Qt`.
2. Open a terminal in the project directory.
3. Create a virtual environment:
   ```
   python3 -m venv .venv
   ```
4. Activate the virtual environment:
   ```
   .\.venv\Scripts\Activate.ps1
   ```
5. Install required packages:
   ```
   pip install -r requirements.txt
   ```
6. Build the resources:
   ```
   .\build.ps1
   ```

### Subsequent Builds
1. Activate the virtual environment (if not already activated):
   ```
   .\.venv\Scripts\Activate.ps1
   ```
2. Run the build script:
   ```
   .\build.ps1
   ```

This will compile the necessary resources for the plugins.