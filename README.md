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

**Note:** This plugin uses Qt 6.6.1 to compile resources. If you are using a different version of Qt you will have to edit `build.ps1` to point to the `rcc.exe` of your Qt version.

### First time

- Install Qt 6.6.1: <https://www.qt.io/download-qt-installer>

- Run the following inside this folder: `python3 -m venv venv`

- Activate env: .\venv\scripts\Activate.ps1

- Run: pip install PyQt5

- Run: `build.ps1` to build the resources

### From then on

- Activate env: .\venv\scripts\Activate.ps1

- Run: `build.ps1` to build the resources
