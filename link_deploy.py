import os
import glob
import json
import traceback
import inspect

import signal
import functools
import traceback
import threading
import subprocess

import multiprocessing
import concurrent.futures

import mobase
import pathlib
from . import common as Dc

import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore
import PyQt5.QtWidgets as QtWidgets

from PyQt5.QtCore import Qt
from PyQt5.QtCore import QThread
from PyQt5.QtCore import QRunnable
from PyQt5.QtCore import QThreadPool
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import qDebug
from PyQt5.QtCore import qWarning
from PyQt5.QtCore import qCritical
from PyQt5.QtCore import QCoreApplication

from PyQt5.QtWidgets import QTreeWidgetItem

class RefreshListWorker(QThread):
    finished_signal = pyqtSignal()
    add_item_signal = pyqtSignal(str)

    __organizer: mobase.IOrganizer

    def __init__(self,  organizer: mobase.IOrganizer, parent=None):
        QThread.__init__(self, parent)
        self.__organizer = organizer
        self.__mods_directory = self.__organizer.modsPath()

    # From: https://github.com/LostDragonist/MO2-Plugins
    def _listDirsRecursive(self, search_dirpaths, prefix=""):
        dirpaths = self.__organizer.listDirectories(prefix)
        for dirpath in dirpaths:
            dirpath = os.path.join(prefix, dirpath)
            search_dirpaths.append(dirpath)
            self._listDirsRecursive(search_dirpaths, dirpath)

    def run(self):
        # Adapted from: https://github.com/LostDragonist/MO2-Plugins
        search_dirpaths = ['']
        
        self._listDirsRecursive(search_dirpaths)
        for dirpath in search_dirpaths:
            for filepath in self.__organizer.findFiles(path=dirpath, filter=lambda x: True):
                # This is a messed up way to discard the mods directory and mod name from the path
                try:
                    filepath = os.path.join(
                        *pathlib.Path(filepath).relative_to(self.__mods_directory).parts[1:]
                    )
                    if "mohidden" in filepath: 
                        continue
                    self.add_item_signal.emit(filepath)
                except ValueError:
                    # Skip files not in the mods directory
                    continue
        self.finished_signal.emit()


class DeployWorker(QThread):
    finished_signal = pyqtSignal()
    set_item_status_signal = pyqtSignal(dict)

    def __init__(self, organizer: mobase.IOrganizer, targetDir, originalDir, symlink, entries, parent=None):
        QThread.__init__(self, parent)
        self.__entries = entries
        self.__symlink = symlink
        self.__organizer = organizer
        self.__target_dir = targetDir
        self.__original_dir = originalDir
        self.__mods_directory = self.__organizer.modsPath()
        self.__max_workers = max(1, multiprocessing.cpu_count() - 1)

    def run(self):
        def link_task(entry):
            origins = self.__organizer.getFileOrigins(entry['filepath'])
            if origins[0]:
                origin = origins[0]
                filepath = entry['filepath']

                if "mohidden" in filepath:
                    return {'entry': entry, 'status': "skipped"}

                target_path = os.path.join(self.__target_dir, filepath)
                target_dirpath = os.path.dirname(target_path)

                mod = self.__organizer.getMod(origin)
                if mod is None:
                    qDebug("Unable to get mod: {}".format(mod_name.encode('utf-8')))
                    return {'entry': entry, 'status': "failed"}

                mod_path = mod.absolutePath()

                if not mod_path.startswith(self.__mods_directory):
                    # Probably DLC or unmanaged mod
                    return {'entry': entry, 'status': "skipped"}

                source_path = os.path.join(mod_path, filepath)
                if os.path.exists(source_path):

                    try:
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    except FileExistsError:
                        pass
                    except:
                        return {'entry': entry, 'status': "failed"}

                    try:
                        #qDebug("os.link('{}', '{}')".format(source_path, target_path).encode("utf-8"))
                        if self.__symlink:
                            os.symlink(source_path, target_path)
                        else:
                            os.link(source_path, target_path)
                        return {'entry': entry, 'status': "linked"}
                    except FileExistsError:
                        return {'entry': entry, 'status': "exists"}
                    except:
                        return {'entry': entry, 'status': "failed"}

                else:
                    return {'entry': entry, 'status': "failed"}
            else:
                return {'entry': entry, 'status': "failed"}

        def link_done_callback(entry, future):
            self.set_item_status_signal.emit(future.result())
        
        with concurrent.futures.ThreadPoolExecutor(max_workers = self.__max_workers) as executor:
            for entry in self.__entries:
                future = executor.submit(link_task, entry)
                future.add_done_callback(functools.partial(link_done_callback, entry))

        self.finished_signal.emit()


class PluginWindow(QtWidgets.QDialog):

    __organizer: mobase.IOrganizer

    def __tr(self, str):
        return QCoreApplication.translate("LinkDeployWindow", str)

    def __init__(self, organizer: mobase.IOrganizer, parent=None):
        self.__organizer = organizer

        self.__cpucount = max(1, multiprocessing.cpu_count() - 1)
        self.__symlink = organizer.pluginSetting(parent.name(), "symlink")

        super(PluginWindow, self).__init__(None)

        self.resize(800, 800)
        self.setWindowIcon(QtGui.QIcon(":/deorder/link_deploy"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Vertical Layout
        verticalLayout = QtWidgets.QVBoxLayout()

        self.__targetDir = organizer.managedGame().dataDirectory().absolutePath()
        # TODO: The following is not used yet
        self.__originalDir = organizer.managedGame().dataDirectory().absolutePath() + "Original"

        # Vertical Layout -> Original Label
        self.noteLabel = QtWidgets.QLabel(self)
        self.noteLabel.setText(self.__tr("""
Warning: This tool will deploy your modlist to the data directory using {}.
Note: (Un/re)depolying is not yet supported meaning you will have to reinstall the game if you want to start fresh.
Note: that there is also no guarantee that the game will not touch and modify your mod files.
Tip: Convert your data directory (Example: <Skyrim Game Dir>/data) to a mod
        """.format(self.__tr('soft links') if self.__symlink else self.__tr('hard links'))))

        verticalLayout.addWidget(self.noteLabel)

        # Vertical Layout -> Target Label
        self.targetDirLabel = QtWidgets.QLabel(self)
        self.targetDirLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)
        self.targetDirLabel.setText(self.__tr("Deployment dir") + ":\n" + self.__targetDir)

        verticalLayout.addWidget(self.targetDirLabel)

        # Vertical Layout -> Original Label
        #self.originalDirLabel = QtWidgets.QLabel(self)
        #self.originalDirLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)
        #self.originalDirLabel.setText(self.__tr("Original dir") + ":\n" + self.__originalDir)

        #verticalLayout.addWidget(self.originalDirLabel)
        
        # Vertical Layout -> Mapping List
        self.mappingList = QtWidgets.QTreeWidget()

        self.mappingList.setColumnCount(1)
        self.mappingList.setRootIsDecorated(False)
        self.mappingList.setAlternatingRowColors(True)

        self.mappingList.header().setVisible(True)
        self.mappingList.headerItem().setText(0, self.__tr("File"))
        #self.mappingList.headerItem().setText(1, self.__tr("Status"))

        verticalLayout.addWidget(self.mappingList)

        # Vertical Layout -> Status Label
        self.statusLabel = QtWidgets.QLabel(self)
        self.statusLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)
        self.statusLabel.setText('...')

        verticalLayout.addWidget(self.statusLabel)
        
        # Vertical Layout -> Button Layout
        buttonLayout = QtWidgets.QHBoxLayout()

        # Vertical Layout -> Button Layout -> Deploy Button
        refreshButton = QtWidgets.QPushButton(self.__tr("&Deploy"), self)
        refreshButton.setIcon(QtGui.QIcon(":/MO/gui/refresh"))
        refreshButton.clicked.connect(self._deploy)
        buttonLayout.addWidget(refreshButton)

        # Vertical Layout -> Button Layout -> Close Button
        closeButton = QtWidgets.QPushButton(self.__tr("&Close"), self)
        closeButton.clicked.connect(self.close)
        buttonLayout.addWidget(closeButton)

        verticalLayout.addLayout(buttonLayout)

        # Vertical Layout
        self.setLayout(verticalLayout)

        # Initial refresh
        self._refreshList()

    def _deploy(self):
        self.statusLabel.setText(self.__tr("Deploying links. Please wait..."))

        entries = []
        root = self.mappingList.invisibleRootItem()
        for item_index in range(root.childCount()):
            entry = root.child(item_index).data(0, Qt.UserRole)
            entry['item_index'] = item_index
            entries.append(entry)
        worker = DeployWorker(self.__organizer, self.__targetDir, self.__originalDir, self.__symlink, entries, self)

        def set_item_status_callback(result):
            entry = result['entry']
            status = result['status']
            filepath = entry['filepath']
            item_index = entry['item_index']
            item = root.child(item_index)
            if status == 'exists':
                item.setBackground(0, Dc.yellow)
            if status == 'linked':
                item.setBackground(0, Dc.green)
            if status == 'failed':
                item.setBackground(0, Dc.red)
            item.setForeground(0, Qt.black)
            self.statusLabel.setText(self.__tr("{} {}").format(filepath, status))

        def finished_callback():
            self.statusLabel.setText(self.__tr("Finished deployment."))

        worker.set_item_status_signal.connect(set_item_status_callback)
        worker.finished_signal.connect(finished_callback)

        worker.start()

    def _refreshList(self):
        self.mappingList.clear()

        worker = RefreshListWorker(self.__organizer, self)

        self.statusLabel.setText(self.__tr("Populating list. Please wait..."))

        def add_item_callback(filepath):
            item = QtWidgets.QTreeWidgetItem(self.mappingList, [filepath, '...'])
            item.setData(0, Qt.UserRole, {"filepath": str(filepath)})
            self.mappingList.addTopLevelItem(item)

        def finished_callback():
            self.statusLabel.setText(self.__tr("Ready for deployment."))
            self.mappingList.resizeColumnToContents(0)

        worker.add_item_signal.connect(add_item_callback)
        worker.finished_signal.connect(finished_callback)

        worker.start()

class PluginTool(mobase.IPluginTool):

    __organizer: mobase.IOrganizer

    NAME = "Link Deploy"
    DESCRIPTION = "Deploy mods using hard links."

    def __tr(self, str):
        return QCoreApplication.translate("LinkDeploy", str)

    def __init__(self):
        self.__window = None
        self.__organizer = None
        self.__parentWidget = None

        super(PluginTool, self).__init__()

    def init(self, organizer):
        from . import resources  # noqa

        self.__organizer = organizer
        return True

    def isActive(self):
        return bool(self.__organizer.pluginSetting(self.NAME, "enabled"))

    def settings(self):
        return [
            mobase.PluginSetting("enabled", self.__tr("Enable plugin"), True),
            mobase.PluginSetting("symlink", self.__tr("Use symlinks/softlinks instead of hardlinks"), False)
        ]

    def display(self):
        self.__window = PluginWindow(self.__organizer, self)
        self.__window.setWindowTitle(self.NAME)
        self.__window.exec_()

    def icon(self):
        return QtGui.QIcon(":/deorder/link_deploy")

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
