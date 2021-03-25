# Mod Organizer 2 Plugins

## Description

- **Merge Plugins Hide**: Hide / unhide plugins that were merged using `Merge Plugins` or `zMerge`
- **Sync Mod Order**: Sync mod order from current profile to another while keeping the (enabled/disabled) state intact

## Installation

Download the latest `.zip` file from the release page and extract it inside Mod Organizer 2's `plugins/` folder.

The plugin will be added to the `Tools` (icon with puzzle pieces) menu.

## Merge Plugins Hide

**Note:** When using zMerge to merge mods Mator recommends to use zMerge's built-in functionality to disable plugins. If you use this zMerge will disable the plugins for you. If you still want to use `Merge Plugins Hide` for example to keep track of the state of the plugins that are merged and quickly enable/disable them you can also set the `hide-type` to `disable` to use the same method as zMerge uses.

You can choose between the following plugin hide methods by changing the `hide-type` setting:

- **mohidden**: Hide using the MO2 virtual file system by adding `.mohidden` to the plugin file
- **optional**: Hide by moving the plugin file to the `optional` directory inside the mod
- **disable**: Hide by disabling the plugin

## Build

### Recommended

#### First time

- Run the following inside this folder: `python3 -m venv venv`

- Activate env if using PowerShell: .\venv\scripts\Activate.ps1
- Activate env if using CMD: call venv/scripts/activate.bat

- Run: pip install PyQt5

- Run: `build.bat` to build the resources

#### From then on

- Activate env if using PowerShell: .\venv\scripts\Activate.ps1
- Activate env if using CMD: call venv/scripts/activate.bat

- Run: `build.bat` to build the resources

### Alternative

- Download: https://github.com/pyqt/python-qt5/tree/master/PyQt5

- Copy & paste the `pyqt5` directory inside this directory

- Run `build.bat` to build the resources
