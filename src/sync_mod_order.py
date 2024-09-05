import os
import glob
import shutil
import datetime

import mobase # type: ignore
from . import common as Dc

import PyQt6.QtGui as QtGui # type: ignore

QAction = QtGui.QAction


import PyQt6.QtWidgets as QtWidgets # type: ignore

from PyQt6.QtCore import Qt # type: ignore

qtUserRole = Qt.ItemDataRole.UserRole
qtScrollBarAlwaysOff = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
qtCustomContextMenu = Qt.ContextMenuPolicy.CustomContextMenu
qtWindowContextHelpButtonHint = Qt.WindowType.WindowContextHelpButtonHint

from PyQt6.QtCore import qDebug, qCritical # type: ignore

from PyQt6.QtCore import QCoreApplication # type: ignore


class PluginWindow(QtWidgets.QDialog):
    def __tr(self, str):
        return QCoreApplication.translate("SyncModOrderWindow", str)

    def __init__(self, organizer, parent=None):
        self.__modListInfo = {}
        self.__profilesInfo = {}
        self.__organizer = organizer

        super(PluginWindow, self).__init__(parent)

        self.resize(500, 500)
        self.setWindowIcon(QtGui.QIcon(":/deorder/sync_mod_order"))
        self.setWindowFlags(self.windowFlags() & ~qtWindowContextHelpButtonHint)

        # Vertical Layout
        verticalLayout = QtWidgets.QVBoxLayout()

        # Vertical Layout -> Merged Mod List (TODO: Better to use QTreeView and model?)
        self.profileList = QtWidgets.QTreeWidget()

        self.profileList.setColumnCount(1)
        self.profileList.setRootIsDecorated(False)

        self.profileList.header().setVisible(True)
        self.profileList.headerItem().setText(0, self.__tr("Profile name"))

        self.profileList.setContextMenuPolicy(qtCustomContextMenu)
        self.profileList.setHorizontalScrollBarPolicy(qtScrollBarAlwaysOff)
        self.profileList.customContextMenuRequested.connect(self.openProfileMenu)

        verticalLayout.addWidget(self.profileList)

        # Vertical Layout -> Button Layout
        buttonLayout = QtWidgets.QHBoxLayout()

        # Vertical Layout -> Button Layout -> Refresh Button
        refreshButton = QtWidgets.QPushButton(self.__tr("&Refresh"), self)
        refreshButton.setIcon(QtGui.QIcon(":/MO/gui/refresh"))
        refreshButton.clicked.connect(self.refreshProfileList)
        buttonLayout.addWidget(refreshButton)

        # Vertical Layout -> Button Layout -> Close Button
        closeButton = QtWidgets.QPushButton(self.__tr("&Close"), self)
        closeButton.clicked.connect(self.close)
        buttonLayout.addWidget(closeButton)

        verticalLayout.addLayout(buttonLayout)

        # Vertical Layout
        self.setLayout(verticalLayout)

        # Build lookup dictionary of all profiles
        self.__profileInfo = self.getProfileInfo()

        # Build lookup dictionary of mods in current profile
        self.__modListInfo = self.getModListInfoByPath(
            os.path.join(self.__organizer.profilePath(), "modlist.txt")
        )

        self.refreshProfileList()

    def getModListInfoByPath(self, path):
        modListInfo = {}
        modListLines = Dc.readLines(path)
        for index, modListLine in enumerate(modListLines):
            modName = modListLine[1:]
            modStateSymbol = modListLine[0]
            modListInfo[modName] = {
                "index": index,
                "name": modName,
                "symbol": modStateSymbol,
            }
        return modListInfo

    def getProfileInfo(self):
        profileInfo = {}
        for path in glob.glob(
            os.path.join(
                Dc.globEscape(self.__organizer.profilePath()),
                os.pardir,
                "*",
                "modlist.txt",
                os.pardir,
            )
        ):
            profilePath = os.path.normpath(path)
            profileName = os.path.basename(profilePath)
            profileInfo[profileName] = {"name": profileName, "path": profilePath}
        return profileInfo

    def refreshProfileList(self):
        self.profileList.clear()
        for profileName in sorted(self.__profileInfo):
            item = QtWidgets.QTreeWidgetItem(self.profileList, [profileName])
            item.setData(0, qtUserRole, {"profileName": profileName})
            self.profileList.addTopLevelItem(item)
        self.profileList.resizeColumnToContents(0)

    def openProfileMenu(self, position):
        selectedItems = self.profileList.selectedItems()
        if selectedItems:
            menu = QtWidgets.QMenu()

            selectedItemsData = [item.data(0, qtUserRole) for item in selectedItems]
            selectedProfiles = [
                selectedItemData["profileName"]
                for selectedItemData in selectedItemsData
            ]

            syncAction = QAction(
                QtGui.QIcon(":/MO/gui/next"),
                self.__tr("&Sync current profile mod order to"),
                self,
            )
            syncAction.setEnabled(True)
            menu.addAction(syncAction)

            action = menu.exec(self.profileList.mapToGlobal(position))

            try:
                if action == syncAction:
                    for profileName in selectedProfiles:
                        profileInfo = self.__profileInfo[profileName]
                        modListPath = os.path.join(profileInfo["path"], "modlist.txt")
                        modListBackupPath = (
                            modListPath
                            + "."
                            + datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
                        )

                        qDebug(self.__tr("Backing up to {}").format(modListBackupPath))
                        shutil.copy(modListPath, modListBackupPath)

                        selectedModListInfo = self.getModListInfoByPath(modListPath)
                        mergedModListInfo = dict(
                            self.__modListInfo, **selectedModListInfo
                        )

                        for modName in list(self.__modListInfo.keys()):
                            mergedModListInfo[modName]["index"] = self.__modListInfo[
                                modName
                            ]["index"]

                        qDebug(self.__tr("Updating {} mod order").format(modListPath))
                        with open(modListPath, "w", encoding="utf-8") as modListFile:
                            for modName, modListEntry in sorted(
                                list(mergedModListInfo.items()),
                                key=lambda x: x[1]["index"],
                            ):
                                modListFile.write(
                                    modListEntry["symbol"] + modListEntry["name"] + "\n"
                                )

                    self.refreshProfileList()
            except Exception as e:
                qCritical(str(e).encode("utf-8"))


class PluginTool(mobase.IPluginTool):

    NAME = "Sync Mod Order"
    DESCRIPTION = (
        "Sync mod order from current profile to another while keeping the "
        "(enabled/disabled) state intact"
    )

    def __tr(self, str):
        return QCoreApplication.translate("SyncModOrder", str)

    def __init__(self):
        self.__window = None
        self.__organizer = None
        self.__parentWidget = None

        super(PluginTool, self).__init__()

    def init(self, organizer):
        from . import resources  # noqa

        self.__organizer = organizer
        return True

    def settings(self):
        return [mobase.PluginSetting("enabled", self.__tr("Enable this plugin"), True)]

    def display(self):
        self.__window = PluginWindow(self.__organizer)
        self.__window.setWindowTitle(self.NAME)
        self.__window.exec()

        # Refresh Mod Organizer mod list to reflect changes
        self.__organizer.refresh()

    def icon(self):

        return QtGui.QIcon(":/deorder/sync_mod_order")

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
