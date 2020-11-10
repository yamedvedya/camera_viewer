# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""

from PyQt5 import QtCore, QtWidgets, QtGui
from src.ui_vimbacam.LogWidget_ui import Ui_LogWidget

# ----------------------------------------------------------------------
class LogWidget(QtWidgets.QWidget):
    """
    """
    PLOT_COLOR = QtGui.QColor(80, 90, 210)
   
    cursorMoved = QtCore.pyqtSignal(float, float)
    
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
        self._logsBuffer.append((int(record.levelno), record.msg))

        self._displayLogs()

    # ----------------------------------------------------------------------
    def _displayLogs(self):
        """
        """
        self._ui.teLogs.clear()

        for level, msg in reversed(self._logsBuffer):
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
        self.restoreGeometry(settings.value("LogWidget/geometry"))
