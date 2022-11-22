# Created by matveyev at 19.08.2021
"""
  Widget for individual camera.
  Has 4 dockable widgets: Frame viewer, Settings, ROI & Marker, PeakSearch.
  Also has his own datasource instance

"""

import logging

from PyQt5 import QtCore, QtWidgets, QtGui

from petra_camera.constants import APP_NAME
from petra_camera.gui.EmptyCameraWidget_ui import Ui_EmptyCameraWindow

logger = logging.getLogger(APP_NAME)


# ----------------------------------------------------------------------
class EmptyCameraWidget(QtWidgets.QMainWindow):

    reinit_camera = QtCore.pyqtSignal(str)

    # ----------------------------------------------------------------------
    def __init__(self, parent, my_name, last_error):
        """
        """
        super(EmptyCameraWidget, self).__init__(parent)

        self._ui = Ui_EmptyCameraWindow()
        self._ui.setupUi(self)

        self._ui.lb_error.setText(last_error)
        self._ui.cmd_reinit_camera.clicked.connect(lambda state, x=my_name: self.reinit_camera.emit(x))

    # ----------------------------------------------------------------------
    def _save_ui_settings(self):
        """Save basic GUI settings.
        """
        settings = QtCore.QSettings(APP_NAME)

        settings.setValue(f"{self.camera_name}/geometry", self.saveGeometry())
        settings.setValue(f"{self.camera_name}/state", self.saveState())

    # ----------------------------------------------------------------------
    def load_ui_settings(self):
        """Load basic GUI settings.
        """
        settings = QtCore.QSettings(APP_NAME)

        try:
            self.restoreGeometry(settings.value(f"{self.camera_name}/geometry"))
        except:
            pass

        try:
            self.restoreState(settings.value(f"{self.camera_name}/state"))
        except:
            pass

    # ----------------------------------------------------------------------
    def clean_close(self):
        pass