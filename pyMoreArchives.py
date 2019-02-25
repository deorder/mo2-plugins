import os
import re
import sys
import glob
import shutil
import datetime
import traceback

import mobase
import functools, operator

import PyQt5
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore
import PyQt5.QtWidgets as QtWidgets

from PyQt5.QtCore import Qt
from PyQt5.QtCore import qDebug
from PyQt5.QtCore import qWarning
from PyQt5.QtCore import qCritical
from PyQt5.QtCore import QCoreApplication

globEscapeRegExp = r'([' + re.escape('[]?*') + '])'

class MoreArchivesPlugin(mobase.IPlugin):

    MODSTATE_UNKNOWN     = 0x00000000
    MODSTATE_EXISTS      = 0x00000001
    MODSTATE_ACTIVE      = 0x00000002
    MODSTATE_ESSENTIAL   = 0x00000004
    MODSTATE_EMPTY       = 0x00000008
    MODSTATE_ENDORSED    = 0x00000010
    MODSTATE_VALID       = 0x00000020
    MODSTATE_ALTERNATE   = 0x00000040

    NAME =  "More Archives"
    DESCRIPTION = "Update plugins.txt by adding dummy plugins entries for archives that have no plugin"

    def __tr(self, str):
        return QCoreApplication.translate("MoreArchives", str)

    def __init__(self):
        self.__window = None
        self.__organizer = None
        self.__parentWidget = None

        super(MoreArchivesPlugin, self).__init__()

    def globEscape(self, text):
        return re.sub(globEscapeRegExp, r'[\1]', text)

    def readLines(self, filename):
        lines = []
        with open(filename, 'r', encoding='utf-8') as file:
            lines = [line.strip() for line in file.readlines()]
        return lines

    def getModByName(self, name):
        return self.__organizer.getMod(name)

    def getModNames(self):
        return self.__organizer.modList().allMods()

    def getMods(self):
        return [self.getModByName(modname) for modname in self.getModNames()]

    def multiGlob(self, patterns):
        return functools.reduce(operator.add, [glob.glob(pattern) for pattern in patterns])

    def multiGlobMod(self, mod, patterns):
        return self.multiGlob([os.path.join(self.globEscape(mod.absolutePath()), pattern) for pattern in patterns])

    def onAboutToRun(self, name):
        plugins = []
        archives = []
        pluginArchives = []
        pluginlessArchives = []

        try:
            pluginListPath = os.path.join(self.__organizer.profilePath(), 'plugins.txt')
            pluginListLines = self.readLines(pluginListPath)
            pluginListBackupPath = pluginListPath + '.more_archives.' +  datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')

            qDebug(self.__tr("Backing up to {}".format(pluginListBackupPath)).encode('utf-8'))
            shutil.copy(pluginListPath, pluginListBackupPath)

            for modIndex, mod in enumerate(self.getMods()):
                modName = mod.name()
                modState = self.__organizer.modList().state(modName)
                if (modState & self.MODSTATE_ACTIVE) == self.MODSTATE_ACTIVE:
                    archivePaths = self.multiGlobMod(mod, ["*.bsa", "*.ba2"])
                    pluginPaths = self.multiGlobMod(mod, ['*.esm', '*.esp', '*.esl'])
                    plugins.extend([{'index': modIndex, 'path': path, 'name': os.path.splitext(os.path.basename(path))[0]} for path in pluginPaths])
                    archives.extend([{'index': modIndex, 'path': path, 'name': os.path.splitext(os.path.basename(path))[0]} for path in archivePaths])

            for archive in archives:
                archivePlugins = [plugin for plugin in plugins if archive['name'].lower().startswith(plugin['name'].lower())]
                if len(archivePlugins) > 0:
                    pluginArchives.append(archive)
                else:
                    pluginlessArchives.append(archive)
                    qDebug(self.__tr("Pluginless archive: {}".format(archive['name'])).encode('utf-8'))

            qDebug(self.__tr("Updating {} plugin list".format(pluginListPath)).encode('utf-8'))
            with open(pluginListPath, 'w') as pluginListFile:
                for pluginListLine in pluginListLines:
                    pluginListFile.write(pluginListLine + '\n')
                for archive in pluginlessArchives:
                    pluginListFile.write("*{}.esp\n".format(archive['name']))

        except Exception as e:
            qCritical(str(e).encode('utf-8'))
            raise

        return True

    def init(self, organizer):
        self.__organizer = organizer
        self.__organizer.onAboutToRun(lambda name: self.onAboutToRun(name))
        #self.__organizer.onFinishedRun(lambda name: self.onFinishedRun(name))
        return True

    def isActive(self):
        return bool(self.__organizer.pluginSetting(self.NAME, "enabled"))

    def settings(self):
        return [
            mobase.PluginSetting("enabled", self.__tr("Enable this plugin"), True)
        ]

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

def createPlugin():
    return MoreArchivesPlugin()