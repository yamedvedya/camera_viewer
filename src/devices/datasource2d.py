# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""

import importlib
import logging
import threading
import time

import numpy as np

from PyQt5 import QtCore


# ----------------------------------------------------------------------
class DataSource2D(QtCore.QObject):
    """
    """
    newFrame = QtCore.pyqtSignal()
    gotError = QtCore.pyqtSignal(str)

    # ----------------------------------------------------------------------
    def __init__(self, settings, parent):
        """
        """
        super(DataSource2D, self).__init__(parent)

        self.settings = settings

        self.log = logging.getLogger("cam_logger")  # is in sync with the main thread? TODO

        self.device_id = ''
        self._device_proxy = None
        self._worker = None

        self._frame_mutex = QtCore.QMutex()  # sync access to frame
        self._last_frame = np.zeros((1, 1))

        self._got_first_frame = False

        self._state = "idle"
        self.fps = 1

    # ----------------------------------------------------------------------
    def _reset_worker(self):
        """
        """
        if self._worker:
            self._state = 'abort'
            self._worker.join()

        self._worker = threading.Thread(target=self.run)

    # ----------------------------------------------------------------------
    def start(self):
        """
        """
        self._reset_worker()
        self._worker.start()

    # ----------------------------------------------------------------------
    def run(self):
        """
        """
        self._start_acquisition()

        while self._state == "running":

            frame = self._device_proxy.maybe_read_frame()
            if frame is not None:
                self._got_first_frame = True
                self._last_frame = frame
                self.newFrame.emit()

            if self._device_proxy.error_flag:
                self.gotError.emit(str(self._device_proxy.error_msg))
                self._state = "abort"

            time.sleep(1/self.fps)
        self.log.info("Closing {}...".format(self.device_id))

        if self._device_proxy:
            self._device_proxy.stop_acquisition()

        self._state = "idle"

    # ----------------------------------------------------------------------
    def _start_acquisition(self):
        """
        """
        if self._device_proxy:
            self._device_proxy.start_acquisition()
            self._state = "running"

    # ----------------------------------------------------------------------
    def stop(self):
        """
        """
        self.log.info("Stop {}...".format(self.device_id))

        if self._state != 'idle':
            self._state = "abort"

        while self._state != 'idle':
            time.sleep(self.fps)

        self.log.debug('CameraDevice stopped')

    # ----------------------------------------------------------------------
    def get_settings(self, setting, cast):

        if self._device_proxy:
            if setting == 'FPS':
                self.fps = self._device_proxy.get_settings('FPS', int)
                return self.fps
            else:
                return self._device_proxy.get_settings(setting, cast)
        else:
            return None

    # ----------------------------------------------------------------------
    def save_settings(self, setting, value):
        if self._device_proxy:
            if setting == 'FPS':
                self.fps = value

            self._device_proxy.save_settings(setting, value)

    # ----------------------------------------------------------------------
    def get_frame(self, mode="copy"):
        """
        """
        return self._last_frame

    # ----------------------------------------------------------------------
    def new_device_proxy(self, name):

        for device in self.settings.getNodes('camera_viewer', 'camera'):
            if device.getAttribute('name') == name:

                self.device_id = name

                try:
                    proxyClass = device.getAttribute("proxy")
                    self.log.info("Loading device proxy {}...".format(proxyClass))

                    module = importlib.import_module("devices.{}".format(proxyClass.lower()))
                    proxy = getattr(module, proxyClass)(self.parent().options.beamlineID, device, self.log)
                    self._device_proxy = proxy
                    return True

                except Exception as ex:
                    self.log.error(ex)
                    return False

        return False

    # ----------------------------------------------------------------------
    def is_running(self):
        return self._state == 'running'

    # ----------------------------------------------------------------------
    def has_motor(self):
        return self._device_proxy.has_motor()

    # ----------------------------------------------------------------------
    def move_motor(self, new_state=None):

        self._device_proxy.move_motor(new_state)

    # ----------------------------------------------------------------------
    def motor_position(self):

        return self._device_proxy.motor_position()

    # ----------------------------------------------------------------------
    def has_counter(self):
        return self._device_proxy.has_counter()

    # ----------------------------------------------------------------------
    def get_counter(self):
        return self._device_proxy.get_counter()

    # ----------------------------------------------------------------------
    def set_counter(self, value):
        self._device_proxy.set_counter(value)

    # ----------------------------------------------------------------------
    def change_picture_size(self, size):
        self._device_proxy.change_picture_size(size)