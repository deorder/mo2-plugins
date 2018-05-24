import os
import sys
import glob

from PyQt5 import QtGui

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
            self.MISSING:    'Missing',
            self.INACTIVE:   'Inactive',
            self.ACTIVE:     'Active'
        }
    def __str__(self):
        return self.__info[self.value]
    MISSING, INACTIVE, ACTIVE = range(3)

class ModPluginsState:
    def __eq__(self, x):
        return self.value == x
    def __init__(self, x):
        self.value = x
        self.__info = {
            self.UNKNOWN:    'Unknown',
            self.INACTIVE:   'Inactive',
            self.MIXED:      'Mixed',
            self.ACTIVE:     'Active'
        }
    def __str__(self):
        return self.__info[self.value]
    UNKNOWN, INACTIVE, MIXED, ACTIVE = range(4)

class ModState:
    UNKNOWN     = 0x00000000
    EXISTS      = 0x00000001
    ACTIVE      = 0x00000002
    ESSENTIAL   = 0x00000004
    EMPTY       = 0x00000008
    ENDORSED    = 0x00000010
    VALID       = 0x00000020
    ALTERNATE   = 0x00000040
    def __init__(self, x):
        self.value = x
        self.__info = {
            self.UNKNOWN:    'Unknown',
            self.EXISTS:     'Exists',
            self.ACTIVE:     'Active',
            self.ESSENTIAL:  'Essential',
            self.EMPTY:      'Empty',
            self.ENDORSED:   'Endorsed',
            self.VALID:      'Valid',
            self.ALTERNATE:  'Alternate'
        }
    def __eq__(self, x):
        return self.value == x
    def __contains__(self, x):
        return (self.value & x) == x
    def __str__(self):
        return ', '.join([self.__info[x] for x in self.__info.keys() if (x in self)])

def readLines(filename):
    lines = []
    with open(filename, 'r') as file:
        lines = [line.strip() for line in file.readlines()]
    return lines

SomeModPluginsActive = [ModPluginsState.ACTIVE, ModPluginsState.MIXED]
SomeModPluginsInactive = [ModPluginsState.INACTIVE, ModPluginsState.MIXED]
