# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""

import PyTango
from petra_camera.utils.tango_utils import TangoDBsInfo

from PyQt5 import QtWidgets

from petra_camera.gui.ImportCameras_ui import Ui_ImportCameras
from petra_camera.constants import CAMERAS_SETTINGS


# ----------------------------------------------------------------------
class ImportCameras(QtWidgets.QDialog):

    def __init__(self, settings):
        super(ImportCameras, self).__init__()
        self._ui = Ui_ImportCameras()
        self._ui.setupUi(self)

        self._settings = settings

        self._boxes = {}

        tango_db = TangoDBsInfo()
        host = PyTango.Database().get_db_host().split('.')[0]
        for camera_name, camera_properties in CAMERAS_SETTINGS.items():
            self._ui.verticalLayout.addWidget(QtWidgets.QLabel(camera_name + ":", self))
            self._boxes[camera_name] = []
            if camera_properties['tango_server'] is not None:
                for device in tango_db.getDeviceNamesByClass(camera_properties['tango_server'], host):
                    check_box = QtWidgets.QCheckBox(device, self)
                    check_box.setChecked(True)
                    self._ui.verticalLayout.addWidget(check_box)
                    self._boxes[camera_name].append(check_box)
            else:
                check_box = QtWidgets.QCheckBox(camera_name, self)
                check_box.setChecked(True)
                self._ui.verticalLayout.addWidget(check_box)
                self._boxes[camera_name].append(check_box)

    # ----------------------------------------------------------------------
    def accept(self) -> None:

        host = PyTango.Database().get_db_host().split('.')[0] + ':10000/'
        cameras_settings = []

        for camera_type, boxes in self._boxes.items():
            for box in boxes:
                if box.isChecked():
                    cameras_settings.append((('name', box.text()),
                                             ('enabled', 'True'),
                                             ('proxy', camera_type),
                                             ('tango_server', host + box.text())))

        self._settings.save_new_options([], cameras_settings)
        
        super(ImportCameras, self).accept()

