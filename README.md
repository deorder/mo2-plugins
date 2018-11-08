# Mod Organizer 2 Plugins

## Description

- **Merge Plugins Hide**: Hide / unhide plugins that were merged using `Merge Plugins` or `zMerge`
- **Sync Mod Order**: Sync mod order from current profile to another while keeping the (enabled/disabled) state intact

## Installation

Copy all files except `LICENSE` and `README.md` inside your `Mod Organizer 2` `plugins` directory.

The plugin will be added to the `Tools` (icon with puzzle pieces) menu.

## Merge Plugins Hide

You can choose between the following plugin hide methods by changing the `hide-type` setting:

- **mohidden**: Hide using the MO2 virtual file system by adding `.mohidden` to the plugin file
- **optional**: Hide by moving the plugin file the the `optional` directory inside the mod
- **disable**: Hide by disabling the plugin

## Build

- Download: https://github.com/pyqt/python-qt5/tree/master/PyQt5

- Copy & paste the `pyqt5` directory inside `data/deorder`

- Run `build.bat` to build the resources

