import os
import sys
import glob

import mobase
import common as Dc

import PyQt5
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore
import PyQt5.QtWidgets as QtWidgets

from PyQt5.QtCore import Qt
from PyQt5.QtCore import qDebug
from PyQt5.QtCore import QCoreApplication

class PluginWindow(QtWidgets.QDialog):

    def __tr(self, str):
        return QCoreApplication.translate("MergePluginsHideWindow", str)

    def __init__(self, organizer, parent = None):
        self.__pluginInfo = {}
        self.__mergedModInfo = {}
        self.__organizer = organizer

        super(PluginWindow, self).__init__(parent)

        self.resize(500, 500)
        self.setWindowIcon(QtGui.QIcon(':/deorder/mergePluginsHide'))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Vertical Layout
        verticalLayout = QtWidgets.QVBoxLayout()

        # Vertical Layout -> Merged Mod List (TODO: Better to use QTreeView and model?)
        self.mergedModList = QtWidgets.QTreeWidget()

        self.mergedModList.setColumnCount(2)
        self.mergedModList.setRootIsDecorated(False)

        self.mergedModList.header().setVisible(True)
        self.mergedModList.headerItem().setText(0, self.__tr("Merge name"))
        self.mergedModList.headerItem().setText(1, self.__tr("Plugins state"))

        self.mergedModList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mergedModList.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.mergedModList.customContextMenuRequested.connect(self.openMergedModMenu)

        verticalLayout.addWidget(self.mergedModList)

        # Vertical Layout -> Button Layout
        buttonLayout = QtWidgets.QHBoxLayout()

        # Vertical Layout -> Button Layout -> Refresh Button
        refreshButton = QtWidgets.QPushButton(self.__tr("&Refresh"), self)
        refreshButton.setIcon(QtGui.QIcon(':/MO/gui/refresh'))
        refreshButton.clicked.connect(self.refreshMergedModList)
        buttonLayout.addWidget(refreshButton)

        # Vertical Layout -> Button Layout -> Close Button
        closeButton = QtWidgets.QPushButton(self.__tr("&Close"), self)
        closeButton.clicked.connect(self.close)
        buttonLayout.addWidget(closeButton)

        verticalLayout.addLayout(buttonLayout)

        # Vertical Layout
        self.setLayout(verticalLayout)

        # Build lookup dictionary of all plugins
        for mod in self.getMods():
            self.addPluginInfoFromMod(mod)

        # Build lookup dictionary of all merged mods
        for mod in self.getMergedMods():
            self.addMergedModInfoFromMod(mod)

        # Add overwrite folder to plugin info dictionary
        self.addPluginInfoFromParams(self.__organizer.overwritePath(), (Dc.ModState.ACTIVE | Dc.ModState.VALID))

        self.refreshMergedModList()

    def tryMoveFile(self, source, target):
        qDebug("Moving {} to {}".format(source, target))
        try:
            # Attempt renaming file even if it does not exist
            os.rename(source, target)
        except:
            # Ignore exception
            pass

    def getModByName(self, name):
        return self.__organizer.getMod(name)

    def getModStateByName(self, name):
        return Dc.ModState(self.__organizer.modList().state(name))

    def getModNames(self):
        return self.__organizer.modList().allMods()

    def getPluginNames(self):
        return self.__organizer.pluginList().pluginNames()

    def getPluginStateByName(self, name):
        pluginInfo = self.__pluginInfo[name]
        if(os.path.isfile(os.path.join(pluginInfo['dirname'], pluginInfo['filename']))):
            return Dc.PluginState(Dc.PluginState.ACTIVE)
        if(os.path.isfile(os.path.join(pluginInfo['dirname'], pluginInfo['filename'] + '.mohidden'))):
            return Dc.PluginState(Dc.PluginState.INACTIVE)
        return Dc.PluginState(Dc.PluginState.MISSING)

    def getPluginStateByNameFromMO2(self, name):
        return Dc.PluginState(self.__organizer.pluginList().state(name))

    def getMods(self):
        return [self.getModByName(modname) for modname in self.getModNames()]

    def isMergedMod(self, mod):
        for path in glob.glob(os.path.join(mod.absolutePath(), "merge", "*_plugins.txt")):
            if os.path.isfile(path):
                return True
        return False

    def getMergedMods(self):
        return [mod for mod in self.getMods() if self.isMergedMod(mod)]

    def getMergedModPlugins(self, mod):
        for path in glob.glob(os.path.join(mod.absolutePath(), "merge", "*_plugins.txt")):
            if os.path.isfile(path):
                return Dc.readLines(path)
        return []

    def getMergedModPluginsState(self, name):
        plugins = self.__mergedModInfo[name]['plugins']
        pluginstates = [self.getPluginStateByName(plugin) for plugin in plugins]
        if(all((pluginstate in [Dc.PluginState.ACTIVE]) for pluginstate in pluginstates)):
            return Dc.ModPluginsState.ACTIVE
        elif(all((pluginstate in [Dc.PluginState.MISSING, Dc.PluginState.INACTIVE]) for pluginstate in pluginstates)):
            return Dc.ModPluginsState.INACTIVE
        elif(any((pluginstate in [Dc.PluginState.MISSING, Dc.PluginState.INACTIVE]) for pluginstate in pluginstates)):
            return Dc.ModPluginsState.MIXED
        else:
            return Dc.ModPluginsState.UNKNOWN

    def addMergedModInfoFromMod(self, mod):
        patterns = ['*.esp', '*.esm', '*.esp.mohidden', '*.esm.mohidden']
        for pattern in patterns:
            for path in glob.glob(os.path.join(mod.absolutePath(), pattern)):
                filename = os.path.basename(path).replace('.mohidden', '')
                self.__mergedModInfo[mod.name()] = {
                    'name': mod.name(),
                    'path': mod.absolutePath(),
                    'plugins': self.getMergedModPlugins(mod),
                    'state': self.getModStateByName(mod.name())
                }

    def addPluginInfoFromMod(self, mod):
        patterns = ['*.esp', '*.esm', '*.esp.mohidden', '*.esm.mohidden']
        for pattern in patterns:
            for path in glob.glob(os.path.join(mod.absolutePath(), pattern)):
                filename = os.path.basename(path).replace('.mohidden', '')
                self.__pluginInfo[filename] = {
                    'filename': filename,
                    'dirname': os.path.dirname(path),
                    'state': self.getModStateByName(mod.name())
                }

    def addPluginInfoFromParams(self, modPath, modState):
        patterns = ['*.esp', '*.esm', '*.esp.mohidden', '*.esm.mohidden']
        for pattern in patterns:
            for path in glob.glob(os.path.join(modPath, pattern)):
                filename = os.path.basename(path).replace('.mohidden', '')
                self.__pluginInfo[filename] = {
                    'filename': filename,
                    'dirname': os.path.dirname(path),
                    'state': modState
                }

    def refreshMergedModList(self):
        self.mergedModList.clear()
        for modName in sorted(self.__mergedModInfo):
            modState = self.getMergedModPluginsState(modName)
            color = {
                Dc.ModPluginsState.UNKNOWN: Dc.red,
                Dc.ModPluginsState.ACTIVE: None,
                Dc.ModPluginsState.MIXED: Dc.yellow,
                Dc.ModPluginsState.INACTIVE: Dc.green
            }[modState]
            stateDescription = {
                Dc.ModPluginsState.UNKNOWN: self.__tr("Unknown"),
                Dc.ModPluginsState.ACTIVE: self.__tr("All plugins active"),
                Dc.ModPluginsState.MIXED: self.__tr("Some plugins active"),
                Dc.ModPluginsState.INACTIVE: self.__tr("All plugins inactive")
            }[modState]
            item = QtWidgets.QTreeWidgetItem(self.mergedModList, [modName, stateDescription])
            for x in range(2):
                if color:
                    item.setBackground(x, color)
                    item.setForeground(x, Qt.black)
                item.setData(x, Qt.UserRole, {"modName": modName, "modState": modState})
            self.mergedModList.addTopLevelItem(item)
        self.mergedModList.resizeColumnToContents(0)

    def openMergedModMenu(self, position):
        selectedItems = self.mergedModList.selectedItems()
        if selectedItems:
            menu = QtWidgets.QMenu()

            selectedItemsData = [item.data(0, Qt.UserRole) for item in selectedItems]
            selectedMods = [selectedItemData['modName'] for selectedItemData in selectedItemsData]
            selectedModsWithEnabled = [selectedItemData['modName'] for selectedItemData in selectedItemsData if (selectedItemData['modState'] in Dc.SomeModPluginsInactive)]
            selectedModsWithDisabled = [selectedItemData['modName'] for selectedItemData in selectedItemsData if (selectedItemData['modState'] in Dc.SomeModPluginsActive)]

            enableAction = QtWidgets.QAction(QtGui.QIcon(':/MO/gui/active'), self.__tr('&Enable plugins'), self)
            enableAction.setEnabled(False)
            menu.addAction(enableAction)
            if selectedModsWithEnabled:
                enableAction.setEnabled(True)

            disableAction = QtWidgets.QAction(QtGui.QIcon(':/MO/gui/inactive'), self.__tr('&Disable plugins'), self)
            disableAction.setEnabled(False)
            menu.addAction(disableAction)
            if selectedModsWithDisabled:
                disableAction.setEnabled(True)

            action = menu.exec_(self.mergedModList.mapToGlobal(position))

            if action == enableAction:
                for selectedMod in selectedModsWithEnabled:
                    for plugin in self.__mergedModInfo[selectedMod]['plugins']:
                        pluginInfo = self.__pluginInfo[plugin]
                        self.tryMoveFile(os.path.join(pluginInfo['dirname'], pluginInfo['filename'] + '.mohidden'), os.path.join(pluginInfo['dirname'], pluginInfo['filename']))
                self.refreshMergedModList()

            if action == disableAction:
                for selectedMod in selectedModsWithDisabled:
                    for plugin in self.__mergedModInfo[selectedMod]['plugins']:
                        pluginInfo = self.__pluginInfo[plugin]
                        self.tryMoveFile(os.path.join(pluginInfo['dirname'], pluginInfo['filename']), os.path.join(pluginInfo['dirname'], pluginInfo['filename'] + '.mohidden'))
                self.refreshMergedModList()

class PluginTool(mobase.IPluginTool):

    NAME =  "Merge Plugins Hide"
    DESCRIPTION = "Hide / unhide plugins that were merged using Merge Plugins."

    def __tr(self, str):
        return QCoreApplication.translate("MergePluginsHide", str)

    def __init__(self):
        self.__window = None
        self.__organizer = None
        self.__parentWidget = None

        super(PluginTool, self).__init__()

    def init(self, organizer):
        from deorder import resources
        self.__organizer = organizer
        return True

    def isActive(self):
        return bool(self.__organizer.pluginSetting(self.NAME, "enabled"))

    def settings(self):
        return [
            mobase.PluginSetting("enabled", self.__tr("Enable this plugin"), True),
            #mobase.PluginSetting("include_disabled_mods", self.__tr("Also hide plugins in disabled mods (when hide_type = mohidden)"), True),
            #mobase.PluginSetting("hide_type", self.__tr("In what way should plugins be hidden: mohidden, disableplugin"), "mohidden")
        ]

    def display(self):
        self.__window = PluginWindow(self.__organizer)
        self.__window.setWindowTitle(self.NAME)
        self.__window.exec_()

        # Refresh Mod Organizer mod list to reflect changes
        self.__organizer.refreshModList()

    def icon(self):

        return QtGui.QIcon(':/deorder/mergePluginsHide')

    def setParentWidget(self, widget):
        self.__parentWidget = widget

    def version(self):
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.final)

    def description(self):
        return self.__tr(self.DESCRIPTION)

    def tooltip(self):
        return self.__tr(self.DESCRIPTION)

    def displayName(self):
        return self.__tr(self.NAME)

    def name(self):
        return self.NAME

    def author(self):
        return "Deorder"