# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""

from PyQt5 import QtWidgets, QtCore
from src.ui_vimbacam.Marker_ui import Ui_Marker

# ----------------------------------------------------------------------
class Marker(QtWidgets.QWidget):

    marker_changed = QtCore.pyqtSignal(int, str, int)
    delete_me = QtCore.pyqtSignal(int)

    # ----------------------------------------------------------------------
    def __init__(self, id):

        super(Marker, self).__init__()

        self._ui = Ui_Marker()
        self._ui.setupUi(self)

        self._ui.but_delete.clicked.connect(lambda status, x=id: self.delete_me.emit(x))
        self._ui.sb_x.valueChanged.connect(lambda value, x=id: self.marker_changed.emit(x, 'x', value))
        self._ui.sb_y.valueChanged.connect(lambda value, x=id: self.marker_changed.emit(x, 'y', value))

    # ----------------------------------------------------------------------
    def _block_signals(self, bool):
        self._ui.sb_x.blockSignals(bool)
        self._ui.sb_y.blockSignals(bool)

    # ----------------------------------------------------------------------
    def set_values(self, values):
        self._block_signals(True)
        self._ui.sb_x.setValue(values['x'])
        self._ui.sb_y.setValue(values['y'])
        self._block_signals(False)
