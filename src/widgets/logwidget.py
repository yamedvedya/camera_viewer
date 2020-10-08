#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de
# Last modified: 2017, November 20
# ----------------------------------------------------------------------

# TODO
"""
"""

import numpy as np

from PyQt4 import QtCore, QtGui

import pyqtgraph as pg

from ui_vimbacam.LogWidget_ui import Ui_LogWidget

# ----------------------------------------------------------------------
class LogWidget(QtGui.QWidget):
    """
    """
    PLOT_COLOR = QtGui.QColor(80, 90, 210)
   
    cursorMoved = QtCore.Signal(float, float)
    
    # ----------------------------------------------------------------------
    def __init__(self, settings, parent):
        """
        """
        super(LogWidget, self).__init__(parent)         # ???? TODO

        self._ui = Ui_LogWidget()
        self._ui.setupUi(self)
     
        self._logsBuffer = []           # (log_level, message) pairs
     
     # ----------------------------------------------------------------------
    def append(self, record):
        """
        """
        #if len(self._logsBuffer) > self.BUFFER_SIZE:        # circular buffer
        #    self._logsBuffer.pop(0)

        #timestamp = record.asctime.split(",")[0]
        #message = "{} {:<8} {}({}) {}".format(timestamp, record.levelname,
        #                                      record.filename, record.lineno,
        #                                      record.msg)
        #self._logsBuffer.append((int(record.levelno), message))
        
        
        self._logsBuffer.append((int(record.levelno), record.msg))

        self._displayLogs()

    # ----------------------------------------------------------------------
    def _displayLogs(self):
        """
        """
        self._ui.teLogs.clear()

        for level, msg in reversed(self._logsBuffer):
            #if level >= self._currentLevel():
            self._ui.teLogs.appendPlainText(msg)

    # ----------------------------------------------------------------------

    def saveUiSettings(self, settings):
        """Save basic GUI settings.
        """
        settings.setValue("LogWidget/geometry", self.saveGeometry())

    # ----------------------------------------------------------------------
    def loadUiSettings(self, settings):
        """Load basic GUI settings.
        """
        self.restoreGeometry(settings.value("LogWidget/geometry").toByteArray())
