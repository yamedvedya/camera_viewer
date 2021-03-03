# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""

from PyQt5 import QtWidgets, QtCore
from src.ui_vimbacam.Marker_ui import Ui_Marker

# ----------------------------------------------------------------------
class Marker(QtWidgets.QWidget):

    marker_changed = QtCore.pyqtSignal()
    delete_me = QtCore.pyqtSignal(int)

    # ----------------------------------------------------------------------
    def __init__(self, id, camera_device):

        super(Marker, self).__init__()

        self._ui = Ui_Marker()
        self._ui.setupUi(self)

        self._camera_device = camera_device
        self.my_id = id

        self._ui.but_delete.clicked.connect(lambda status, x=id: self.delete_me.emit(x))

        self._ui.sb_x.valueChanged.connect(lambda value: self.save_value('x', value))
        self._ui.sb_y.valueChanged.connect(lambda value: self.save_value('y', value))
        self._ui.chk_visible.clicked.connect(lambda value: self.save_value('visible', value))

    # ----------------------------------------------------------------------
    def _block_signals(self, flag):
        self._ui.sb_x.blockSignals(flag)
        self._ui.sb_y.blockSignals(flag)
        self._ui.chk_visible.blockSignals(flag)

    # ----------------------------------------------------------------------
    def update_values(self):
        self._block_signals(True)
        self._ui.sb_x.setValue(self._camera_device.markers[self.my_id]['x'])
        self._ui.sb_y.setValue(self._camera_device.markers[self.my_id]['y'])
        self._ui.chk_visible.setChecked(self._camera_device.markers[self.my_id]['visible'])
        self._block_signals(False)

    # ----------------------------------------------------------------------
    def save_value(self, param, value):
        self._camera_device.set_marker_value(self.my_id, param, value)
        self.marker_changed.emit()
