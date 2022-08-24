# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""
import threading

try:
    import PyTango
except ImportError:
    pass
from contextlib import contextmanager
import logging


from PyQt5 import QtCore

from petra_camera.widgets.base_widget import BaseWidget
from petra_camera.main_window import APP_NAME
from petra_camera.gui.PositionControl_ui import Ui_PositionControl

logger = logging.getLogger(APP_NAME)

REFRESH_PERIOD = 1


# ----------------------------------------------------------------------
class PositionControl(BaseWidget):
    """
    """
    WIDGET_NAME = 'PositionControl'

    # ----------------------------------------------------------------------
    def __init__(self, parent):
        """
        """
        super(PositionControl, self).__init__(parent)

        self._ui = Ui_PositionControl()
        self._ui.setupUi(self)

        self.setup_limits()

        # to prevent double code run
        self._my_mutex = QtCore.QMutex()
        self._stop_position_reader = threading.Event()

        for param in ['pan', 'tilt', 'focus', 'zoom']:
            getattr(self._ui, f'sb_move_{param}').editingFinished.connect(lambda x=param: self.move_to_sb(x))

        for param in ['pan', 'tilt', 'focus', 'zoom']:
            getattr(self._ui, f'sl_pos_{param}').valueChanged.connect(lambda value, x=param: self.move_to_sl(x, value))

        self._position_reader = PositionReader(self._camera_device, self._stop_position_reader)
        self._position_reader.position_ready.connect(self.display_position)
        self._position_reader.start()

    # ----------------------------------------------------------------------
    def setup_limits(self):
        with self.block_signals():
            for limit in ['min', 'max']:
                for cast_type, elements in zip([float, int], [['pan', 'tilt'], ['focus', 'zoom']]):
                    for param in elements:
                        value = self._camera_device.get_settings(f'{limit}_{param}', cast_type)
                        getattr(self._ui, f'lb_{limit}_{param}').setText(f'{value:.{0 if cast_type==int else 2}f}')
                        if limit == 'min':
                            getattr(self._ui, f'sl_pos_{param}').setMinimum(value)
                            getattr(self._ui, f'sb_move_{param}').setMinimum(value)
                        else:
                            getattr(self._ui, f'sl_pos_{param}').setMaximum(value)
                            getattr(self._ui, f'sb_move_{param}').setMaximum(value)

    # ----------------------------------------------------------------------
    @contextmanager
    def block_signals(self):
        for param in ['pan', 'tilt', 'focus', 'zoom']:
            getattr(self._ui, f'sb_move_{param}').blockSignals(True)
            getattr(self._ui, f'sl_pos_{param}').blockSignals(True)

        yield

        for param in ['pan', 'tilt', 'focus', 'zoom']:
            getattr(self._ui, f'sb_move_{param}').blockSignals(False)
            getattr(self._ui, f'sl_pos_{param}').blockSignals(False)

    # ----------------------------------------------------------------------
    def display_position(self):
        with QtCore.QMutexLocker(self._my_mutex):
            with self.block_signals():
                for params, decimals in zip([['pan', 'tilt'], ['zoom', 'focus']], [2, 0]):
                    for param in params:
                        for ui in ['sl_pos', 'sb_move']:
                            if not getattr(self._ui, f'{ui}_{param}').hasFocus():
                                value = getattr(self._position_reader, f'{param}')
                                getattr(self._ui, f'{ui}_{param}').setValue(value)
                                getattr(self._ui, f'gb_{param}').setTitle(f'{param.capitalize()}: {value:.{decimals}f}')

    # ----------------------------------------------------------------------
    def move_to_sb(self, param):
        self._camera_device.save_settings(param, getattr(self._ui, f'sb_move_{param}').value())

    # ----------------------------------------------------------------------
    def move_to_sl(self, param, value):
        self._camera_device.save_settings(param, value)


# ----------------------------------------------------------------------
class PositionReader(QtCore.QThread):

    position_ready = QtCore.pyqtSignal()

    def __init__(self, camera_device, stop_request):
        super().__init__()
        self._camera_device = camera_device
        self._stop_requested = stop_request

        self.pan = None
        self.tilt = None
        self.focus = None
        self.zoom = None

    # ----------------------------------------------------------------------
    def run(self):
        while not self._stop_requested.is_set():

            self.pan = self._camera_device.get_settings('pan', float)
            self.tilt = self._camera_device.get_settings('tilt', float)
            self.focus = self._camera_device.get_settings('focus', int)
            self.zoom = self._camera_device.get_settings('zoom', int)

            self.position_ready.emit()

            QtCore.QThread.msleep(REFRESH_PERIOD*1000)