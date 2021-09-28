import os
import re
import sys
import glob

from PyQt5 import QtGui
from PyQt5.QtCore import qDebug
from PyQt5.QtCore import qWarning

red = QtGui.QColor(255, 170, 170)
green = QtGui.QColor(205, 222, 135)
yellow = QtGui.QColor(255, 238, 170)

darkRed = QtGui.QColor(155, 70, 70)
darkGreen = QtGui.QColor(105, 122, 35)
darkYellow = QtGui.QColor(155, 138, 70)


class PluginState:
    def __eq__(self, x):
        return self.value == x

    def __init__(self, x):
        self.value = x
        self.__info = {
            self.MISSING: "Missing",
            self.INACTIVE: "Inactive",
            self.ACTIVE: "Active",
        }

    def __str__(self):
        return self.__info[self.value]

    MISSING, INACTIVE, ACTIVE = list(range(3))


class ModPluginsState:
    def __eq__(self, x):
        return self.value == x

    def __init__(self, x):
        self.value = x
        self.__info = {
            self.UNKNOWN: "Unknown",
            self.INACTIVE: "Inactive",
            self.MIXED: "Mixed",
            self.ACTIVE: "Active",
        }

    def __str__(self):
        return self.__info[self.value]

    UNKNOWN, INACTIVE, MIXED, ACTIVE = list(range(4))


SomeModPluginsActive = [ModPluginsState.ACTIVE, ModPluginsState.MIXED]
SomeModPluginsInactive = [ModPluginsState.INACTIVE, ModPluginsState.MIXED]


class ModState:
    UNKNOWN = 0x00000000
    EXISTS = 0x00000001
    ACTIVE = 0x00000002
    ESSENTIAL = 0x00000004
    EMPTY = 0x00000008
    ENDORSED = 0x00000010
    VALID = 0x00000020
    ALTERNATE = 0x00000040

    def __init__(self, x):
        self.value = x
        self.__info = {
            self.UNKNOWN: "Unknown",
            self.EXISTS: "Exists",
            self.ACTIVE: "Active",
            self.ESSENTIAL: "Essential",
            self.EMPTY: "Empty",
            self.ENDORSED: "Endorsed",
            self.VALID: "Valid",
            self.ALTERNATE: "Alternate",
        }

    def __eq__(self, x):
        return self.value == x

    def __contains__(self, x):
        return (self.value & x) == x

    def __str__(self):
        return ", ".join(
            [self.__info[x] for x in list(self.__info.keys()) if (x in self)]
        )


globEscapeRegExp = r"([" + re.escape("[]?*") + "])"


def globEscape(text):
    return re.sub(globEscapeRegExp, r"[\1]", text)


def tryMoveFile(source, target):
    qDebug("Moving {} to {}".format(source, target).encode("utf-8"))
    try:
        # Attempt renaming file even if it does not exist
        os.rename(source, target)
    except:
        # Ignore exception
        pass


def tryCreateDir(path):
    qDebug("Creating dir {}".format(path).encode("utf-8"))
    try:
        # Attempt creating directory
        os.mkdir(path)
    except:
        # Ignore exception
        pass


def readLines(filename):
    lines = []
    with open(filename, "r", encoding="utf-8") as file:
        lines = [line.strip() for line in file.readlines()]
    # for line in lines:
    #    qDebug(line.encode('utf-8'))
    return lines


def getModByName(organizer, name):
    return organizer.getMod(name)


def getModStateByName(organizer, name):
    return ModState(organizer.modList().state(name))


def getModNames(organizer):
    return organizer.modList().allMods()


def getPluginNames(organizer):
    return organizer.pluginList().pluginNames()


def getPluginStateByName(organizer, name):
    return PluginState(organizer.pluginList().state(name))


def setPluginStateByName(organizer, name, state):
    return organizer.pluginList().setState(name, state)


def getMods(organizer):
    return [getModByName(organizer, modname) for modname in getModNames(organizer)]
