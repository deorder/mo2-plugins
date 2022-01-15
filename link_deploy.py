import os
import json
import datetime

import functools

import multiprocessing
import concurrent.futures

import mobase
import pathlib
from . import common as Dc

from enum import Enum
from typing import Union

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

from json.decoder import JSONDecodeError


def is_relative_to(from_path, to_path):
    try:
        from_path.relative_to(to_path)
        return True
    except ValueError:
        return False


class StateOperation(Enum):
    LINK = 0
    REMOVE = 1
    CREATE_IN_STATE = 2
    UPDATE_IN_STATE = 3
    REMOVE_FROM_STATE = 4
    LINK_TO_OVERWRITE = 5
    BACKUP_EXISTING = 6


class StateManager:
    def __tr(self, str: str):
        return QCoreApplication.translate("LinkDeployStateManager", str)

    def __init__(self, organizer: mobase.IOrganizer, target_data_dir: str, target_game_dir: str, state_file_path: str, symlink: bool = False):
        self.state = {}
        self.__symlink = symlink
        self.__organizer = organizer
        self.__target_data_dir = target_data_dir
        self.__target_game_dir = target_game_dir
        self.__state_file_path = state_file_path
        self.__state_file_dir = os.path.dirname(self.__state_file_path)

    def loadState(self):
        try:
            with open(self.__state_file_path) as state_file:
                self.state = json.load(state_file)
        except FileNotFoundError:
            pass
        except JSONDecodeError:
            qWarning(self.__tr("Invalid or corrupted state file {}").format(self.__state_file_path).encode("utf-8"))
        except:
            qWarning(self.__tr("Could not read state file {}").format(self.__state_file_path).encode("utf-8"))

    def saveState(self):
        try:
            os.makedirs(self.__state_file_dir, exist_ok=True)
        except FileExistsError:
            pass
        except:
            qWarning(self.__tr("Could not create state file dir {}").format(self.__state_file_dir).encode("utf-8"))
        try:
            with open(self.__state_file_path, "w") as state_file:
                json.dump(self.state, state_file)
        except:
            qWarning(self.__tr("Could not write state file {}").format(self.__state_file_path).encode("utf-8"))

    def getStateEntry(self, file_path: str):
        entry = {}

        entry["file_path"] = file_path

        state: Union[None, dict] = self.state.get(file_path)
        entry["state_exists"] = file_path in self.state

        target_path = entry["target_path"] = None
        target_stat = entry["target_stat"] = None
        target_exists = entry["target_exists"] = False
        target_path_dir = entry["target_path_dir"] = None
        path = pathlib.Path(file_path)
        if path.parts[0] == "root":
            target_path = entry["target_path"] = os.path.join(self.__target_game_dir, file_path)
            target_path_dir = entry["target_path_dir"] = os.path.dirname(target_path)
        else:
            target_path = entry["target_path"] = os.path.join(self.__target_data_dir, file_path)
            target_path_dir = entry["target_path_dir"] = os.path.dirname(target_path)
        try:
            target_stat = entry["target_stat"] = os.stat(target_path, follow_symlinks=True)
            target_exists = entry["target_exists"] = True
        except OSError:
            pass

        source_path = entry["source_path"] = None
        source_stat = entry["source_stat"] = None
        source_exists = entry["source_exists"] = False
        source_path_dir = entry["source_path_dir"] = None
        origins = self.__organizer.getFileOrigins(file_path)
        if origins[0]:
            origin = origins[0]
            mod = self.__organizer.getMod(origin)
            if mod is not None:
                mod_path = mod.absolutePath()
                source_path = entry["source_path"] = os.path.join(mod_path, file_path)
                source_path_dir = entry["source_path_dir"] = os.path.dirname(source_path)
                try:
                    source_stat = entry["source_stat"] = os.stat(source_path, follow_symlinks=True)
                    source_exists = entry["source_exists"] = True
                except OSError:
                    pass

        entry["source_target_samefile"] = False
        if source_stat and target_stat:
            if self.__symlink:
                entry["source_target_samefile"] = source_stat.st_mtime == target_stat.st_mtime and source_stat.st_ctime == target_stat.st_ctime and source_stat.st_size == target_stat.st_size
            else:
                entry["source_target_samefile"] = source_stat.st_dev == target_stat.st_dev and source_stat.st_ino == target_stat.st_ino

        entry["state_target_samefile"] = False
        if state and target_stat:
            if self.__symlink:
                entry["state_target_samefile"] = state.get("mtime") == target_stat.st_mtime and state.get("ctime") == target_stat.st_ctime and state.get("size") == target_stat.st_size
            else:
                entry["state_target_samefile"] = state.get("dev") == target_stat.st_dev and state.get("ino") == target_stat.st_ino

        entry["state_source_samefile"] = False
        if state and source_stat:
            if self.__symlink:
                entry["state_source_samefile"] = state.get("mtime") == source_stat.st_mtime and state.get("ctime") == source_stat.st_ctime and state.get("size") == source_stat.st_size
            else:
                entry["state_source_samefile"] = state.get("dev") == source_stat.st_dev and state.get("ino") == source_stat.st_ino

        if source_stat:
            entry["state_new"] = {"mtime": source_stat.st_mtime, "ctime": source_stat.st_ctime, "size": source_stat.st_size, "dev": source_stat.st_dev, "ino": source_stat.st_ino}
        else:
            entry["state_new"] = None

        if state:
            entry["state_old"] = {"mtime": state.get("mtime"), "ctime": state.get("ctime"), "size": state.get("size"), "dev": state.get("dev"), "ino": state.get("ino")}
        else:
            entry["state_old"] = None

        return entry


class RefreshListWorker(QThread):
    finished_signal = pyqtSignal()
    add_item_signal = pyqtSignal(str)

    __organizer: mobase.IOrganizer

    def __tr(self, str):
        return QCoreApplication.translate("LinkDeployRefreshWorker", str)

    def __init__(self, organizer: mobase.IOrganizer, state_manager: StateManager, parent=None):
        QThread.__init__(self, parent)
        self.__is_running = True
        self.__organizer = organizer
        self.__state_manager = state_manager
        self.__mods_directory = self.__organizer.modsPath()
        self.__overwrite_directory = self.__organizer.overwritePath()

    # From: https://github.com/LostDragonist/MO2-Plugins
    def _listDirsRecursive(self, search_dirpaths, prefix=""):
        dirpaths = self.__organizer.listDirectories(prefix)
        for dirpath in dirpaths:
            dirpath = os.path.join(prefix, dirpath)
            search_dirpaths.append(dirpath)
            self._listDirsRecursive(search_dirpaths, dirpath)

    def run(self):
        # Adapted from: https://github.com/LostDragonist/MO2-Plugins
        search_dirpaths = [""]

        self._listDirsRecursive(search_dirpaths)
        for dirpath in search_dirpaths:
            for file_path in self.__organizer.findFiles(path=dirpath, filter=lambda x: True):
                if not self.__is_running:
                    break

                if "mohidden" in file_path:
                    continue

                if not os.path.exists(file_path):
                    continue

                p = pathlib.Path(file_path)
                if is_relative_to(p, self.__mods_directory):
                    file_path = os.path.join(*p.relative_to(self.__mods_directory).parts[1:])
                elif is_relative_to(p, self.__overwrite_directory):
                    file_path = os.path.join(*p.relative_to(self.__overwrite_directory).parts[0:])
                else:
                    continue

                entry = self.__state_manager.getStateEntry(file_path)

                self.add_item_signal.emit(entry)

        self.finished_signal.emit()

    def stop(self):
        self.__is_running = False


class DeployWorker(QThread):
    finished_signal = pyqtSignal()
    set_item_status_signal = pyqtSignal(dict)

    def __tr(self, str):
        return QCoreApplication.translate("LinkDeployWorker", str)

    def __init__(self, organizer: mobase.IOrganizer, state_manager: StateManager, symlink: bool, entries, parent=None):
        QThread.__init__(self, parent)
        self.__is_running = True
        self.__entries = entries
        self.__symlink = symlink
        self.__organizer = organizer
        self.__state_manager = state_manager
        self.__max_workers = max(1, multiprocessing.cpu_count() - 1)

    def run(self):
        def link_task(entry):
            if not self.__is_running:
                return {"entry": entry, "status": "canceled"}

            origins = self.__organizer.getFileOrigins(entry["filepath"])
            if origins[0]:
                origin = origins[0]
                filepath = entry["filepath"]

                if "mohidden" in filepath:
                    return {"entry": entry, "status": "skipped"}

                target_path = os.path.join(self.__target_dir, filepath)
                target_dirpath = os.path.dirname(target_path)

                mod = self.__organizer.getMod(origin)
                if mod is None:
                    qWarning("Unable to get mod: {}".format(mod.name().encode("utf-8")))
                    return {"entry": entry, "status": "failed"}

                mod_path = mod.absolutePath()

                source_path = os.path.join(mod_path, filepath)
                if os.path.exists(source_path):

                    try:
                        os.makedirs(target_dirpath, exist_ok=True)
                    except FileExistsError:
                        pass
                    except:
                        qWarning(self.__tr("Could not create path {}").format(target_dirpath).encode("utf-8"))
                        return {"entry": entry, "status": "failed"}

                    try:
                        if self.__symlink:
                            os.symlink(source_path, target_path)
                        else:
                            os.link(source_path, target_path)
                        return {"entry": entry, "status": "linked"}
                    except FileExistsError:
                        if not os.path.samefile(source_path, target_path):
                            if not os.path.exists(target_path + ".mo2_original"):
                                try:
                                    os.rename(target_path, target_path + ".mo2_original")
                                except:
                                    qWarning(self.__tr("Could not move away original {}").format(target_path).encode("utf-8"))
                                    return {"entry": entry, "status": "failed"}
                            else:
                                try:
                                    os.rename(target_path, target_path + ".mo2_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"))
                                except:
                                    qWarning(self.__tr("Could not move away {}").format(target_path).encode("utf-8"))
                                    return {"entry": entry, "status": "failed"}
                            try:
                                if self.__symlink:
                                    os.symlink(source_path, target_path)
                                else:
                                    os.link(source_path, target_path)
                                return {"entry": entry, "status": "linked"}
                            except:
                                qWarning(self.__tr("Could not create link {}, after moving away").format(target_path).encode("utf-8"))
                                return {"entry": entry, "status": "failed"}
                        else:
                            return {"entry": entry, "status": "already deployed"}
                    except:
                        qWarning(self.__tr("Could not create link {}").format(target_path).encode("utf-8"))
                        return {"entry": entry, "status": "failed"}

                else:
                    qWarning(self.__tr("Source path {} does not exist").format(source_path).encode("utf-8"))
                    return {"entry": entry, "status": "failed"}
            else:
                qWarning(self.__tr("No origins found").encode("utf-8"))
                return {"entry": entry, "status": "failed"}

        def link_done_callback(entry, future):
            self.set_item_status_signal.emit(future.result())

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.__max_workers) as executor:
            for entry in self.__entries:
                if not self.__is_running:
                    break
                future = executor.submit(link_task, entry)
                future.add_done_callback(functools.partial(link_done_callback, entry))

        self.finished_signal.emit()

    def stop(self):
        self.__is_running = False


class PluginWindow(QtWidgets.QDialog):

    __organizer: mobase.IOrganizer

    def __tr(self, str):
        return QCoreApplication.translate("LinkDeployWindow", str)

    def __init__(self, organizer: mobase.IOrganizer, parent=None):
        self.__organizer = organizer

        self.__deploy_worker = None
        self.__refresh_worker = None
        self.__cpucount = max(1, multiprocessing.cpu_count() - 1)
        self.__symlink = organizer.pluginSetting(parent.name(), "symlink")

        super(PluginWindow, self).__init__(None)

        self.resize(800, 800)
        self.setWindowIcon(QtGui.QIcon(":/deorder/link_deploy"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.__target_data_dir = organizer.managedGame().dataDirectory().absolutePath()
        self.__target_game_dir = organizer.managedGame().gameDirectory().absolutePath()

        self.__state_file_dir = self.__target_game_dir
        self.__state_file_path = os.path.join(self.__state_file_dir, ".mo2_state")

        self.__state_manager = StateManager(self.__organizer, self.__target_data_dir, self.__target_game_dir, self.__state_file_path, self.__symlink)

        # Vertical Layout
        verticalLayout = QtWidgets.QVBoxLayout()

        # Vertical Layout -> Original Label
        self.noteLabel = QtWidgets.QLabel(self)
        self.noteLabel.setText(
            self.__tr(
                """
Warning: This tool will deploy your modlist to the data directory using {}.
Note: (Un/re)depolying is not yet supported meaning you will have to reinstall the game if you want to start fresh.
Note: that there is also no guarantee that the game will not touch and modify your mod files.
Tip: Convert your data directory (Example: <Skyrim Game Dir>/data) to a mod
        """.format(
                    self.__tr("soft links") if self.__symlink else self.__tr("hard links")
                )
            )
        )

        verticalLayout.addWidget(self.noteLabel)

        # Vertical Layout -> Target Label
        self.targetDirLabel = QtWidgets.QLabel(self)
        self.targetDirLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)
        self.targetDirLabel.setText(self.__tr("Deployment dir") + ":\n" + self.__targetDir)

        verticalLayout.addWidget(self.targetDirLabel)

        # Vertical Layout -> Original Label
        # self.originalDirLabel = QtWidgets.QLabel(self)
        # self.originalDirLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)
        # self.originalDirLabel.setText(self.__tr("Original dir") + ":\n" + self.__originalDir)

        # verticalLayout.addWidget(self.originalDirLabel)

        # Vertical Layout -> Mapping List
        self.mappingList = QtWidgets.QTreeWidget()

        self.mappingList.setColumnCount(1)
        self.mappingList.setRootIsDecorated(False)
        self.mappingList.setAlternatingRowColors(True)

        self.mappingList.header().setVisible(True)
        self.mappingList.headerItem().setText(0, self.__tr("File"))
        # self.mappingList.headerItem().setText(1, self.__tr("Status"))

        verticalLayout.addWidget(self.mappingList)

        # Vertical Layout -> Status Label
        self.statusLabel = QtWidgets.QLabel(self)
        self.statusLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)
        self.statusLabel.setText("...")

        verticalLayout.addWidget(self.statusLabel)

        # Vertical Layout -> Button Layout
        buttonLayout = QtWidgets.QHBoxLayout()

        # Vertical Layout -> Button Layout -> Deploy Button
        self.__deployButton = QtWidgets.QPushButton(self.__tr("&Deploy"), self)
        self.__deployButton.setIcon(QtGui.QIcon(":/MO/gui/refresh"))
        self.__deployButton.clicked.connect(self._deploy)
        self.__deployButton.setDisabled(True)
        buttonLayout.addWidget(self.__deployButton)

        # Vertical Layout -> Button Layout -> Close Button
        closeButton = QtWidgets.QPushButton(self.__tr("&Close"), self)
        closeButton.clicked.connect(self._close)
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
            entry["item_index"] = item_index
            entries.append(entry)
        self.__deploy_worker = DeployWorker(self.__organizer, self.__state_manager, self.__symlink, entries, self)

        def set_item_status_callback(result):
            entry = result["entry"]
            status = result["status"]
            filepath = entry["filepath"]
            item_index = entry["item_index"]
            item = root.child(item_index)
            if status == "already deployed":
                item.setBackground(0, Dc.yellow)
            if status == "linked":
                item.setBackground(0, Dc.green)
            if status == "failed":
                item.setBackground(0, Dc.red)
            item.setForeground(0, Qt.black)
            self.statusLabel.setText(self.__tr("{} {}").format(filepath, self.__tr(status)))

        def finished_callback():
            self.statusLabel.setText(self.__tr("Finished deployment."))
            self.__deployButton.setDisabled(True)
            self.__state_manager.saveState()

        self.__deploy_worker.set_item_status_signal.connect(set_item_status_callback)
        self.__deploy_worker.finished_signal.connect(finished_callback)

        self.__deploy_worker.start()

    def _refreshList(self):
        self.mappingList.clear()

        self.__state_manager.loadState()
        self.__refresh_worker = RefreshListWorker(self.__organizer, self.__state_manager, self)

        self.statusLabel.setText(self.__tr("Populating list. Please wait..."))

        def add_item_callback(entry):
            item = QtWidgets.QTreeWidgetItem(self.mappingList, [entry["file_path"], "..."])
            item.setData(0, Qt.UserRole, entry)
            self.mappingList.addTopLevelItem(item)

        def finished_callback():
            self.statusLabel.setText(self.__tr("Ready for deployment."))
            self.mappingList.resizeColumnToContents(0)
            self.__deployButton.setDisabled(False)
            self.__state_manager.saveState()

        self.__refresh_worker.add_item_signal.connect(add_item_callback)
        self.__refresh_worker.finished_signal.connect(finished_callback)

        self.__refresh_worker.start()

    def _close(self):
        if self.__refresh_worker:
            self.__refresh_worker.stop()
            self.__refresh_worker.quit()
            self.__refresh_worker.wait()

        if self.__deploy_worker:
            self.__deploy_worker.stop()
            self.__deploy_worker.quit()
            self.__deploy_worker.wait()

        self.close()


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
        return [mobase.PluginSetting("enabled", self.__tr("Enable plugin"), True), mobase.PluginSetting("symlink", self.__tr("Use symlinks/softlinks instead of hardlinks"), False)]

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
