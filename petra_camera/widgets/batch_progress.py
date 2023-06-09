# Created by matveyev at 06.05.2021

import logging

from PyQt5 import QtCore, QtWidgets

from petra_camera.gui.batch_ui import Ui_batch

from petra_camera.constants import APP_NAME
logger = logging.getLogger(APP_NAME)


# ----------------------------------------------------------------------
class BatchProgress(QtWidgets.QWidget):

    # ----------------------------------------------------------------------
    def __init__(self):
        super(BatchProgress, self).__init__()

        self._ui = Ui_batch()
        self._ui.setupUi(self)

        self._statuses = {}

    # --------------------------------------------------------------------
    def set_title(self, mode):
        self.setWindowTitle(mode)

    # --------------------------------------------------------------------
    def clear(self):
        logger.debug("Reset progress")
        for layout in [self._ui.layout_names, self._ui.layout_status]:
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                if item:
                    w = layout.itemAt(i).widget()
                    if w:
                        layout.removeWidget(w)
                        w.setVisible(False)

        self._ui.pb_progress.setValue(0)

    # ----------------------------------------------------------------------
    def new_cameras_set(self, camera_list):
        logger.debug(f"New camera set: {camera_list}")
        self._statuses = {}
        for camera_id, camera_name in camera_list:
            self._ui.layout_names.addWidget(QtWidgets.QLabel(camera_name))
            lb_status = QtWidgets.QLabel("")
            self._ui.layout_status.addWidget(lb_status)
            self._statuses[camera_id] = lb_status

        self.setFixedSize(self.layout().sizeHint())

    # ----------------------------------------------------------------------
    def set_camera_progress(self, camera_id, status):
        logger.debug(f"New camera status {camera_id}: {status}")
        self._statuses[camera_id].setText(status)

    # ----------------------------------------------------------------------
    def total_progress(self, progress):
        self._ui.pb_progress.setValue(progress*100)