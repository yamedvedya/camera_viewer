# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""

import PyTango
try:
    from HasyUtils import getDeviceNamesByClass
except:
    from petra_camera.utils.tango_utils import getDeviceNamesByClass

from PyQt5 import QtWidgets

from petra_camera.gui.ImportCameras_ui import Ui_ImportCameras

TYPES_TO_SEARCH = ['LMScreen', 'TangoVimba', 'AXISCamera']


# ----------------------------------------------------------------------
class ImportCameras(QtWidgets.QDialog):

    def __init__(self, settings):
        super(ImportCameras, self).__init__()
        self._ui = Ui_ImportCameras()
        self._ui.setupUi(self)

        self._settings = settings

        self._ui.verticalLayout.insertWidget(0, QtWidgets.QLabel("Petra status:", self))
        check_box = QtWidgets.QCheckBox('Status screen', self)
        check_box.setChecked(True)
        self._ui.verticalLayout.insertWidget(1, check_box)
        self._boxes = {'PetraStatus': check_box}

        counter = 2
        host = PyTango.Database().get_db_host().split('.')[0]
        for camera_type in TYPES_TO_SEARCH:
            self._ui.verticalLayout.insertWidget(counter, QtWidgets.QLabel(camera_type + ":", self))
            counter += 1
            self._boxes[camera_type] = []
            for device in getDeviceNamesByClass(camera_type, host):
                check_box = QtWidgets.QCheckBox(device, self)
                check_box.setChecked(True)
                self._ui.verticalLayout.insertWidget(counter, check_box)
                counter += 1
                self._boxes[camera_type].append(check_box)

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

        self._settings.set_options([], cameras_settings)
        
        super(ImportCameras, self).accept()

