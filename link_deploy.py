import os
import datetime
import functools
import multiprocessing
import concurrent.futures
import pathlib

from . import common as Dc

import PyQt6.QtGui as QtGui

import PyQt6.QtWidgets as QtWidgets

QFramePanel = QtWidgets.QFrame.Shape.Panel
QFrameSunken = QtWidgets.QFrame.Shadow.Sunken

from PyQt6.QtCore import (
    Qt,
    QThread,
    pyqtSignal,
    qWarning,
    QCoreApplication,
)

qtBlack = Qt.GlobalColor.black
qtUserRole = Qt.ItemDataRole.UserRole
qtWindowContextHelpButtonHint = Qt.WindowType.WindowContextHelpButtonHint



class FileEntry:
    def __init__(self, filepath: str, filetreeentry: mobase.FileTreeEntry = None):
        self.filepath = filepath
        self.filetreeentry = filetreeentry


def isRelativeTo(from_path: pathlib.Path, to_path: pathlib.Path) -> bool:
    try:
        from_path.relative_to(to_path)
        return True
    except ValueError:
        return False


def listDirectoriesRecursive(
    organizer: mobase.IOrganizer, prefix: str = ""
) -> Generator[str, None, None]:
    dirpaths = organizer.listDirectories(prefix)
    for dirpath in dirpaths:
        full_path = os.path.join(prefix, dirpath)
        yield full_path
        yield from listDirectoriesRecursive(organizer, full_path)


def generateEntries(
    organizer: mobase.IOrganizer,
) -> Generator[FileEntry, None, None]:
    mods_directory = organizer.modsPath()
    overwrite_directory = organizer.overwritePath()
    data_dir = organizer.managedGame().dataDirectory().absolutePath()

    for dirpath in listDirectoriesRecursive(organizer):
        for filepath in organizer.findFiles(path=dirpath, filter=lambda x: True):
            if "mohidden" in filepath or not os.path.exists(filepath):
                continue

            p = pathlib.Path(filepath)
            if isRelativeTo(p, pathlib.Path(mods_directory)):
                filepath = os.path.join(*p.relative_to(mods_directory).parts[1:])
            elif isRelativeTo(p, pathlib.Path(overwrite_directory)):
                filepath = os.path.join(*p.relative_to(overwrite_directory).parts[0:])
            elif isRelativeTo(p, pathlib.Path(data_dir)):
                filepath = os.path.join(*p.relative_to(data_dir).parts[1:])
            else:
                qWarning(
                    QCoreApplication.translate("LinkDeployWorker", "Unknown path {}")
                    .format(filepath)
                    .encode("utf-8")
                )
                continue

            yield FileEntry(filepath)


class DeployWorker(QThread):
    finish_signal = pyqtSignal()
    message_signal = pyqtSignal(dict)

    def __tr(self, text: str) -> str:
        return QCoreApplication.translate("LinkDeployWorker", text)

    def __init__(
        self,
        organizer: mobase.IOrganizer,
        dataTargetDir: str,
        gameTargetDir: str,
        symlink: bool,
        redirect_root: bool,
        entries_generator: Generator[Dict[str, str], None, None],
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.__is_running = True
        self.__entries_generator = entries_generator
        self.__symlink = symlink
        self.__organizer = organizer
        self.__data_target_dir = dataTargetDir
        self.__game_target_dir = gameTargetDir
        self.__redirect_root = redirect_root
        self.__max_workers = min(4, max(1, multiprocessing.cpu_count() - 1))

    def run(self) -> None:
        def link_task(entry: Dict[str, str]) -> Dict[str, str]:
            if not self.__is_running:
                return {"entry": entry, "status": "canceled"}

            origins = self.__organizer.getFileOrigins(entry["filepath"])
            if not origins[0]:
                qWarning(self.__tr("No origins found").encode("utf-8"))
                return {"entry": entry, "status": "failed"}

            origin = origins[0]
            filepath = entry["filepath"]
            filepathsegments = filepath.split(os.sep)

            if "mohidden" in filepathsegments:
                return {"entry": entry, "status": "skipped"}

            target_path = (
                os.path.join(self.__game_target_dir, *filepathsegments[1:])
                if self.__redirect_root and filepathsegments[0] == "root"
                else os.path.join(self.__data_target_dir, filepath)
            )

            target_dirpath = os.path.dirname(target_path)
            mod = self.__organizer.modList().getMod(origin)
            if mod is None:
                qWarning(self.__tr("Unable to get mod").encode("utf-8"))
                return {"entry": entry, "status": "failed"}

            source_path = os.path.join(mod.absolutePath(), filepath)
            if not os.path.exists(source_path):
                qWarning(
                    self.__tr("Source path {} does not exist")
                    .format(source_path)
                    .encode("utf-8")
                )
                return {"entry": entry, "status": "failed"}

            try:
                os.makedirs(target_dirpath, exist_ok=True)
            except Exception as e:
                qWarning(
                    self.__tr("Could not create path {}: {}")
                    .format(target_dirpath, str(e))
                    .encode("utf-8")
                )
                return {"entry": entry, "status": "failed"}

            try:
                if self.__symlink:
                    os.symlink(source_path, target_path)
                else:
                    os.link(source_path, target_path)
                return {"entry": entry, "status": "linked"}
            except FileExistsError:
                if not os.path.samefile(source_path, target_path):
                    backup_path = (
                        target_path + ".mo2_original"
                        if not os.path.exists(target_path + ".mo2_original")
                        else target_path
                        + ".mo2_"
                        + datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
                    )
                    try:
                        os.rename(target_path, backup_path)
                    except Exception as e:
                        qWarning(
                            self.__tr("Could not move away original {}: {}")
                            .format(target_path, str(e))
                            .encode("utf-8")
                        )
                        return {"entry": entry, "status": "failed"}

                    try:
                        if self.__symlink:
                            os.symlink(source_path, target_path)
                        else:
                            os.link(source_path, target_path)
                        return {"entry": entry, "status": "linked"}
                    except Exception as e:
                        qWarning(
                            self.__tr("Could not create link {}: {}")
                            .format(target_path, str(e))
                            .encode("utf-8")
                        )
                        return {"entry": entry, "status": "failed"}
                else:
                    return {"entry": entry, "status": "already deployed"}
            except Exception as e:
                qWarning(
                    self.__tr("Could not create link {}: {}")
                    .format(target_path, str(e))
                    .encode("utf-8")
                )
                return {"entry": entry, "status": "failed"}

        def link_done_callback(
            entry: Dict[str, str], future: concurrent.futures.Future
        ) -> None:
            self.message_signal.emit(future.result())

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.__max_workers
        ) as executor:
            for entry in self.__entries_generator:
                if not self.__is_running:
                    break
                future = executor.submit(link_task, entry)
                future.add_done_callback(functools.partial(link_done_callback, entry))

        self.finish_signal.emit()

    def stop(self) -> None:
        self.__is_running = False


class PluginWindow(QtWidgets.QDialog):

    __organizer: mobase.IOrganizer

    def __tr(self, str):
        return QCoreApplication.translate("LinkDeployWindow", str)

    def __init__(
        self, organizer: mobase.IOrganizer, parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super(PluginWindow, self).__init__(None)

        self.__organizer = organizer
        self.__deploy_worker: Optional[DeployWorker] = None
        self.__symlink = organizer.pluginSetting(parent.name(), "symlink") == "true"

        self.init_ui()

    def init_ui(self) -> None:
        self.resize(800, 400)
        self.setWindowIcon(QtGui.QIcon(":/deorder/link_deploy"))
        self.setWindowFlags(self.windowFlags() & ~qtWindowContextHelpButtonHint)

        vertical_layout = QtWidgets.QVBoxLayout()

        self.noteLabel = QtWidgets.QLabel(self)
        self.noteLabel.setText(
            self.__tr(
                """
Warning: This tool will deploy your modlist using {}.
Note: that there is also no guarantee that the game will not touch and modify your mod files.
Note: (Un/re)deploying is not supported meaning you will have to reinstall the game if you want to start fresh.
                """.format(
                    self.__tr("soft links")
                    if self.__symlink
                    else self.__tr("hard links")
                )
            )
        )
        vertical_layout.addWidget(self.noteLabel)

        self.documentsDirLabel = QtWidgets.QLabel(self)
        self.documentsDirLabel.setFrameStyle(QFramePanel | QFrameSunken)
        self.documentsDirLabel.setText(
            self.__tr("Documents dir")
            + ":\n"
            + self.__organizer.managedGame().documentsDirectory().absolutePath()
        )
        vertical_layout.addWidget(self.documentsDirLabel)

        self.documentsTargetDirectory = QtWidgets.QLabel(self)
        self.documentsTargetDirectory.setText(self.__tr("Documents target dir:"))
        vertical_layout.addWidget(self.documentsTargetDirectory)

        self.documentsTargetDirEdit = QtWidgets.QLineEdit(self)
        self.documentsTargetDirEdit.setText(
            self.__organizer.managedGame().documentsDirectory().absolutePath()
            + " "
            + self.__organizer.profileName()
        )
        vertical_layout.addWidget(self.documentsTargetDirEdit)

        self.saveDirLabel = QtWidgets.QLabel(self)
        self.saveDirLabel.setFrameStyle(QFramePanel | QFrameSunken)
        self.saveDirLabel.setText(
            self.__tr("Save dir")
            + ":\n"
            + self.__organizer.managedGame().savesDirectory().absolutePath()
        )
        vertical_layout.addWidget(self.saveDirLabel)

        self.saveTargetDirectory = QtWidgets.QLabel(self)
        self.saveTargetDirectory.setText(self.__tr("Saves target dir:"))
        vertical_layout.addWidget(self.saveTargetDirectory)

        if (
            self.__organizer.managedGame()
            .savesDirectory()
            .absolutePath()
            .startswith(
                self.__organizer.managedGame().documentsDirectory().absolutePath()
            )
        ):
            documents_dir = (
                self.__organizer.managedGame().documentsDirectory().absolutePath()
                + " "
                + self.__organizer.profileName()
            )
            save_dir = (
                self.__organizer.managedGame()
                .documentsDirectory()
                .relativeFilePath(
                    self.__organizer.managedGame().savesDirectory().absolutePath()
                )
            )
            self.saveTargetDirEdit = QtWidgets.QLineEdit(self)
            self.saveTargetDirEdit.setText(documents_dir + "/" + save_dir)
        else:
            self.saveTargetDirEdit = QtWidgets.QLineEdit(self)
            self.saveTargetDirEdit.setText(
                self.__organizer.managedGame().savesDirectory().absolutePath()
                + " "
                + self.__organizer.profileName()
            )
        vertical_layout.addWidget(self.saveTargetDirEdit)

        self.gameDirLabel = QtWidgets.QLabel(self)
        self.gameDirLabel.setFrameStyle(QFramePanel | QFrameSunken)
        self.gameDirLabel.setText(
            self.__tr("Game dir")
            + ":\n"
            + self.__organizer.managedGame().gameDirectory().absolutePath()
        )
        vertical_layout.addWidget(self.gameDirLabel)

        self.gameTargetDirLabel = QtWidgets.QLabel(self)
        self.gameTargetDirLabel.setText(self.__tr("Game target dir:"))
        vertical_layout.addWidget(self.gameTargetDirLabel)

        self.gameTargetDirEdit = QtWidgets.QLineEdit(self)
        self.gameTargetDirEdit.setText(
            self.__organizer.managedGame().gameDirectory().absolutePath()
            + " "
            + self.__organizer.profileName()
        )
        vertical_layout.addWidget(self.gameTargetDirEdit)

        self.dataDirLabel = QtWidgets.QLabel(self)
        self.dataDirLabel.setFrameStyle(QFramePanel | QFrameSunken)
        self.dataDirLabel.setText(
            self.__tr("Data dir")
            + ":\n"
            + self.__organizer.managedGame().dataDirectory().absolutePath()
        )
        vertical_layout.addWidget(self.dataDirLabel)

        self.dataTargetDirLabel = QtWidgets.QLabel(self)
        self.dataTargetDirLabel.setText(self.__tr("Data target dir:"))
        vertical_layout.addWidget(self.dataTargetDirLabel)

        if (
            self.__organizer.managedGame()
            .dataDirectory()
            .absolutePath()
            .startswith(self.__organizer.managedGame().gameDirectory().absolutePath())
        ):
            game_dir = (
                self.__organizer.managedGame().gameDirectory().absolutePath()
                + " "
                + self.__organizer.profileName()
            )
            data_dir = (
                self.__organizer.managedGame()
                .gameDirectory()
                .relativeFilePath(
                    self.__organizer.managedGame().dataDirectory().absolutePath()
                )
            )
            self.dataTargetDirEdit = QtWidgets.QLineEdit(self)
            self.dataTargetDirEdit.setText(game_dir + "/" + data_dir)
        else:
            self.dataTargetDirEdit = QtWidgets.QLineEdit(self)
            self.dataTargetDirEdit.setText(
                self.__organizer.managedGame().dataDirectory().absolutePath()
                + " "
                + self.__organizer.profileName()
            )
        vertical_layout.addWidget(self.dataTargetDirEdit)

        self.modsDirLabel = QtWidgets.QLabel(self)
        self.modsDirLabel.setFrameStyle(QFramePanel | QFrameSunken)
        self.modsDirLabel.setText(
            self.__tr("Mods dir") + ":\n" + self.__organizer.modsPath()
        )
        vertical_layout.addWidget(self.modsDirLabel)

        self.overwriteDirLabel = QtWidgets.QLabel(self)
        self.overwriteDirLabel.setFrameStyle(QFramePanel | QFrameSunken)
        self.overwriteDirLabel.setText(
            self.__tr("Overwrite dir") + ":\n" + self.__organizer.overwritePath()
        )
        vertical_layout.addWidget(self.overwriteDirLabel)

        self.redirectRootCheckbox = QtWidgets.QCheckBox(
            self.__tr("Redirect 'root' subdirectories in mods to game dir"),
            self,
        )
        self.redirectRootCheckbox.setChecked(True)
        vertical_layout.addWidget(self.redirectRootCheckbox)

        self.statusLabel = QtWidgets.QLabel(self)
        self.statusLabel.setFrameStyle(QFramePanel | QFrameSunken)
        self.statusLabel.setText("...")
        vertical_layout.addWidget(self.statusLabel)

        button_layout = QtWidgets.QHBoxLayout()

        self.__deployButton = QtWidgets.QPushButton(self.__tr("&Deploy"), self)
        self.__deployButton.setIcon(QtGui.QIcon(":/MO/gui/refresh"))
        self.__deployButton.clicked.connect(self._deploy)
        button_layout.addWidget(self.__deployButton)

        closeButton = QtWidgets.QPushButton(self.__tr("&Close"), self)
        closeButton.clicked.connect(self._close)
        button_layout.addWidget(closeButton)

        vertical_layout.addLayout(button_layout)
        self.setLayout(vertical_layout)

    def _deploy(self) -> None:
        self.statusLabel.setText(self.__tr("Deploying links. Please wait..."))

        entries_generator = generateEntries(self.__organizer)

        for entry in entries_generator:
            qInfo(
                QCoreApplication.translate("LinkDeploy", "Found file {}/{}")
                .format(entry.filepath, entry.filetreeentry.path())
                .encode("utf-8")
            )

        # self.__deploy_worker = DeployWorker(
        #     self.__organizer,
        #     self.dataTargetDirEdit.text(),
        #     self.gameTargetDirEdit.text(),
        #     self.__symlink,
        #     self.redirectRootCheckbox.isChecked(),
        #     entries_generator,
        #     self,
        # )

        # self.__deploy_worker.message_signal.connect(self._message_handler)
        # self.__deploy_worker.finish_signal.connect(self._finish_handler)

        # self.__deploy_worker.start()

    def _message_handler(self, result: Dict[str, str]) -> None:
        entry = result["entry"]
        status = result["status"]
        filepath = entry["filepath"]
        self.statusLabel.setText(self.__tr("{} {}").format(filepath, self.__tr(status)))
        if status == "failed":
            qWarning(self.__tr("Failed linking: {}").format(filepath).encode("utf-8"))
        if status == "skipped":
            qInfo(self.__tr("Skipped linking: {}").format(filepath).encode("utf-8"))

    def _finish_handler(self) -> None:
        self.statusLabel.setText(self.__tr("Finished deployment."))
        self.__deployButton.setDisabled(True)

    def _close(self) -> None:
        if self.__deploy_worker:
            self.__deploy_worker.stop()
            self.__deploy_worker.quit()
            self.__deploy_worker.wait()
        self.close()


class PluginTool(mobase.IPluginTool):
    NAME = "Link Deploy"
    DESCRIPTION = "Deploy mods using hard or soft links."

    def __init__(self) -> None:
        super().__init__()
        self.__window: Optional[PluginWindow] = None
        self.__organizer: Optional[mobase.IOrganizer] = None

    def __tr(self, text: str) -> str:
        return QCoreApplication.translate("LinkDeploy", text)

    def init(self, organizer: mobase.IOrganizer) -> bool:
        from . import resources  # noqa

        self.__organizer = organizer
        return bool(self.__organizer.pluginSetting(self.NAME, "agree"))

    def settings(self) -> List[mobase.PluginSetting]:
        return [
            mobase.PluginSetting("enabled", self.__tr("Enable plugin"), False),
            mobase.PluginSetting(
                "agree",
                self.__tr(
                    "I agree that this plugin is experimental and may cause data loss."
                ),
                False,
            ),
            mobase.PluginSetting(
                "symlink",
                self.__tr("Use symlinks/softlinks instead of hardlinks"),
                False,
            ),
        ]

    def display(self) -> None:
        self.__window = PluginWindow(self.__organizer, self)
        self.__window.setWindowTitle(self.NAME)
        self.__window.exec()

    def icon(self) -> QtGui.QIcon:
        return QtGui.QIcon(":/deorder/link_deploy")

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 1, 0, mobase.ReleaseType.final)

    def description(self) -> str:
        return self.__tr(self.DESCRIPTION)

    def tooltip(self) -> str:
        return self.__tr(self.DESCRIPTION)

    def displayName(self) -> str:
        return self.__tr(self.NAME)

    def name(self) -> str:
        return self.NAME

    def author(self) -> str:
        return "Deorder"
