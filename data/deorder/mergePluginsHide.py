import os
import sys
import glob
import json
import traceback

import mobase
from . import common as Dc

import PyQt5
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore
import PyQt5.QtWidgets as QtWidgets

from PyQt5.QtCore import Qt
from PyQt5.QtCore import qDebug
from PyQt5.QtCore import qWarning
from PyQt5.QtCore import qCritical
from PyQt5.QtCore import QCoreApplication

class PluginWindow(QtWidgets.QDialog):

    def __tr(self, str):
        return QCoreApplication.translate("MergePluginsHideWindow", str)

    def __init__(self, organizer, parent = None):
        self.__pluginInfo = {}
        self.__mergedModInfo = {}
        self.__organizer = organizer

        super(PluginWindow, self).__init__(None)

        self.__hide_type = organizer.pluginSetting(parent.name(), "hide-type")
        self.__only_active_mods = organizer.pluginSetting(parent.name(), "only-active-mods")

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
        self.mergedModList.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

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

        qDebug("Hide Type: {}".format(self.__hide_type).encode('utf-8'))
        qDebug("Only Active Mods: {}".format(self.__only_active_mods).encode('utf-8'))

        # Vertical Layout
        self.setLayout(verticalLayout)

        # Build lookup dictionary of all plugins
        for mod in Dc.getMods(self.__organizer):
            modState = Dc.getModStateByName(self.__organizer, mod.name())
            if((self.__only_active_mods == True and (Dc.ModState.ACTIVE) in modState) or (self.__only_active_mods == False)):
                self.addPluginInfoFromParams(mod.absolutePath(), modState)

        # Add overwrite folder to plugin info dictionary
        self.addPluginInfoFromParams(self.__organizer.overwritePath(), (Dc.ModState.ACTIVE | Dc.ModState.VALID))

        # Build lookup dictionary of all merged mods
        for mod in self.getMergedMods():
            self.addMergedModInfoFromMod(mod)

        self.refreshMergedModList()

    def isMergedMod(self, mod):
        for path in glob.glob(os.path.join(Dc.globEscape(mod.absolutePath()), "merge*", "merge.json")):
            if os.path.isfile(path):
                return True
        for path in glob.glob(os.path.join(Dc.globEscape(mod.absolutePath()), "merge*", "*_plugins.txt")):
            if os.path.isfile(path):
                return True
        return False

    def getMergedMods(self):
        return [mod for mod in Dc.getMods(self.__organizer) if self.isMergedMod(mod) and ((Dc.ModState.ACTIVE | Dc.ModState.VALID) in Dc.getModStateByName(self.__organizer, mod.name()))]

    def getMergedModPlugins(self, mod):
        for path in glob.glob(os.path.join(Dc.globEscape(mod.absolutePath()), "merge*", "merge.json")):
            if os.path.isfile(path):
                plugins = []
                with open(path, 'r', encoding='utf-8') as file:
                    merge = json.load(file)
                    plugins = [plugin['filename'] for plugin in merge['plugins']]
                return plugins
        for path in glob.glob(os.path.join(Dc.globEscape(mod.absolutePath()), "merge*", "*_plugins.txt")):
            if os.path.isfile(path):
                return Dc.readLines(path)
        return []

    def getPluginStateByName(self, name):
        if name in self.__pluginInfo:
            pluginInfo = self.__pluginInfo[name]
            if self.__hide_type == "mohidden":
                if(all([os.path.isfile(os.path.join(mod['dirname'], pluginInfo['filename'])) for mod in pluginInfo['mods']])):
                    return Dc.PluginState(Dc.PluginState.ACTIVE)
                if(all([os.path.isfile(os.path.join(mod['dirname'], pluginInfo['filename'] + '.mohidden')) for mod in pluginInfo['mods']])):
                    return Dc.PluginState(Dc.PluginState.INACTIVE)
            if self.__hide_type == "optional":
                if(all([os.path.isfile(os.path.join(mod['dirname'], pluginInfo['filename'])) for mod in pluginInfo['mods']])):
                    return Dc.PluginState(Dc.PluginState.ACTIVE)
                if(all([os.path.isfile(os.path.join(mod['dirname'], 'optional', pluginInfo['filename'])) for mod in pluginInfo['mods']])):
                    return Dc.PluginState(Dc.PluginState.INACTIVE)
            if self.__hide_type == "disable":                
                if(all([os.path.isfile(os.path.join(mod['dirname'], pluginInfo['filename'])) for mod in pluginInfo['mods']])):
                    return Dc.getPluginStateByName(self.__organizer, pluginInfo['filename'])
        else:
            qWarning(self.__tr("Plugin {} missing".format(name)).encode('utf-8'))
        return Dc.PluginState(Dc.PluginState.MISSING)

    def getMergedModPluginsState(self, name):
        if name in self.__mergedModInfo:
            plugins = self.__mergedModInfo[name]['plugins']
            pluginstates = [self.getPluginStateByName(plugin) for plugin in plugins]            
            if(all((pluginstate in [Dc.PluginState.ACTIVE]) for pluginstate in pluginstates)):
                return Dc.ModPluginsState.ACTIVE
            elif(all((pluginstate in [Dc.PluginState.MISSING, Dc.PluginState.INACTIVE]) for pluginstate in pluginstates)):
                return Dc.ModPluginsState.INACTIVE
            elif(any((pluginstate in [Dc.PluginState.MISSING, Dc.PluginState.INACTIVE]) for pluginstate in pluginstates)):
                return Dc.ModPluginsState.MIXED
        else:
            qWarning(self.__tr("Merged mod {} missing".format(name)).encode('utf-8'))
        return Dc.ModPluginsState.UNKNOWN

    def addMergedModInfoFromMod(self, mod):
        self.__mergedModInfo[mod.name()] = {
            'name': mod.name(),
            'path': mod.absolutePath(),
            'plugins': self.getMergedModPlugins(mod),
            'modstate': Dc.getModStateByName(self.__organizer, mod.name())
        }

    def addPluginInfoFromMod(self, mod):
        return self.addPluginInfoFromParams(mod.absolutePath(), Dc.getModStateByName(self.__organizer, mod.name()))

    def addPluginInfoFromParams(self, modPath, modState):
        mod = {'modstate': modState, 'dirname': modPath}
        patterns = ['*.esp', '*.esm']
        if self.__hide_type == "mohidden":
            patterns = ['*.esp', '*.esm', '*.esp.mohidden', '*.esm.mohidden']
        if self.__hide_type == "optional":
            patterns = ['*.esp', '*.esm', os.path.join('optional', '*.esp'), os.path.join('optional', '*.esm')]
        for pattern in patterns:
            for path in glob.glob(os.path.join(Dc.globEscape(modPath), pattern)):
                if self.__hide_type == "mohidden":
                    filename = os.path.basename(path).replace('.mohidden', '')
                    if filename in self.__pluginInfo:
                        self.__pluginInfo[filename]['mods'] += [mod]
                    else:
                        self.__pluginInfo[filename] = {
                            'filename': os.path.basename(path).replace('.mohidden', ''),
                            'mods': [mod]
                        }
                if self.__hide_type in ["optional", "disable"]:
                    filename = os.path.basename(path)                    
                    if filename in self.__pluginInfo:
                        self.__pluginInfo[filename]['mods'] += [mod]
                    else:
                        self.__pluginInfo[filename] = {
                            'filename': os.path.basename(path),
                            'mods': [mod]
                        }

    def refreshMergedModList(self):
        self.mergedModList.clear()
        for modName in sorted(self.__mergedModInfo):
            modPluginsState = self.getMergedModPluginsState(modName)
            color = {
                Dc.ModPluginsState.UNKNOWN: Dc.red,
                Dc.ModPluginsState.ACTIVE: None,
                Dc.ModPluginsState.MIXED: Dc.yellow,
                Dc.ModPluginsState.INACTIVE: Dc.green
            }[modPluginsState]
            stateDescription = {
                Dc.ModPluginsState.UNKNOWN: self.__tr("Unknown"),
                Dc.ModPluginsState.ACTIVE: self.__tr("All plugins active"),
                Dc.ModPluginsState.MIXED: self.__tr("Some plugins active"),
                Dc.ModPluginsState.INACTIVE: self.__tr("All plugins inactive")
            }[modPluginsState]
            item = QtWidgets.QTreeWidgetItem(self.mergedModList, [modName, stateDescription])
            for x in range(2):
                if color:
                    item.setBackground(x, color)
                    item.setForeground(x, Qt.black)
                item.setData(x, Qt.UserRole, {"modName": modName, "modPluginsState": modPluginsState})
            self.mergedModList.addTopLevelItem(item)
        self.mergedModList.resizeColumnToContents(0)

    def openMergedModMenu(self, position):
        selectedItems = self.mergedModList.selectedItems()
        if selectedItems:
            menu = QtWidgets.QMenu()

            selectedItemsData = [item.data(0, Qt.UserRole) for item in selectedItems]
            selectedMods = [selectedItemData['modName'] for selectedItemData in selectedItemsData]
            selectedModsWithEnabled = [selectedItemData['modName'] for selectedItemData in selectedItemsData if (selectedItemData['modPluginsState'] in Dc.SomeModPluginsInactive)]
            selectedModsWithDisabled = [selectedItemData['modName'] for selectedItemData in selectedItemsData if (selectedItemData['modPluginsState'] in Dc.SomeModPluginsActive)]

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

            # Catch and log exceptional side-effects
            try:
                if action == enableAction:
                    for selectedMod in selectedModsWithEnabled:
                        for plugin in self.__mergedModInfo[selectedMod]['plugins']:
                            if plugin in self.__pluginInfo:
                                pluginInfo = self.__pluginInfo[plugin]

                                for mod in pluginInfo['mods']:
                                    if self.__hide_type == "mohidden":
                                        Dc.tryMoveFile(os.path.join(mod['dirname'], pluginInfo['filename'] + '.mohidden'), os.path.join(mod['dirname'], pluginInfo['filename']))
                                    if self.__hide_type == "optional":
                                        Dc.tryMoveFile(os.path.join(mod['dirname'], 'optional', pluginInfo['filename']), os.path.join(mod['dirname'], pluginInfo['filename']))
                                    if self.__hide_type == "disable":
                                        Dc.setPluginStateByName(self.__organizer, pluginInfo['filename'], Dc.PluginState.ACTIVE)

                if action == disableAction:
                    for selectedMod in selectedModsWithDisabled:
                        for plugin in self.__mergedModInfo[selectedMod]['plugins']:
                            if plugin in self.__pluginInfo:
                                pluginInfo = self.__pluginInfo[plugin]

                                for mod in pluginInfo['mods']:
                                    if self.__hide_type == "mohidden":
                                        Dc.tryMoveFile(os.path.join(mod['dirname'], pluginInfo['filename']), os.path.join(mod['dirname'], pluginInfo['filename'] + '.mohidden'))
                                    if self.__hide_type == "optional":
                                        Dc.tryCreateDir(os.path.join(mod['dirname'], 'optional'))
                                        Dc.tryMoveFile(os.path.join(mod['dirname'], pluginInfo['filename']), os.path.join(mod['dirname'], 'optional', pluginInfo['filename']))
                                    if self.__hide_type == "disable":
                                        Dc.setPluginStateByName(self.__organizer, pluginInfo['filename'], Dc.PluginState.INACTIVE)

                self.refreshMergedModList()
            except Exception as e:
                qCritical(traceback.format_exc().encode('utf-8'))
                qCritical(str(e).encode('utf-8'))

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
            mobase.PluginSetting("only-active-mods", self.__tr("Only hide/unhide in active mods"), True),
            mobase.PluginSetting("hide-type", self.__tr("In what way should plugins be hidden: mohidden (Hide file), optional (Move to optional dir), disable (Disable plugins)"), "mohidden")
        ]

    def display(self):
        self.__window = PluginWindow(self.__organizer, self)
        self.__window.setWindowTitle(self.NAME)
        self.__window.exec_()

        # Refresh Mod Organizer mod list to reflect changes where files were changed outside MO2
        if self.__organizer.pluginSetting(self.name(), "hide-type") in ["mohidden", "optional"]:
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
