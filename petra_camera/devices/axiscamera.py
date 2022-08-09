# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""Axis camera proxy
"""

import time
import numpy as np
import logging

try:
    import PyTango
except ImportError:
    pass

from threading import Thread
from distutils.util import strtobool

from petra_camera.devices.base_camera import BaseCamera
from petra_camera.main_window import APP_NAME

logger = logging.getLogger(APP_NAME)

_base_settings_map = {'FPS': ("device_proxy", "FPSLimit"),
                      'max_width': ("device_proxy", "ImageWidth"),
                      'max_height': ("device_proxy", "ImageHeight"),
                      'pan': ("device_proxy", "Pan"),
                      'max_pan': ("device_proxy", "MaxPan"),
                      'min_pan': ("device_proxy", "MinPan"),
                      'tilt': ("device_proxy", "Tilt"),
                      'max_tilt': ("device_proxy", "MaxTilt"),
                      'min_tilt': ("device_proxy", "MinTilt"),
                      'zoom': ("device_proxy", "Zoom"),
                      'max_zoom': ("device_proxy", "MaxZoom"),
                      'min_zoom': ("device_proxy", "MinZoom"),
                      'focus': ("device_proxy", "Focus"),
                      'max_focus': ("device_proxy", "MaxFocus"),
                      'min_focus': ("device_proxy", "MinFocus"),
                      }


# ----------------------------------------------------------------------
class AXISCamera(BaseCamera):
    """Proxy to a physical TANGO device.
    """

    START_DELAY = 1
    STOP_DELAY = 0.5

    START_ATTEMPTS = 2

    visible_layouts = ('FPS', 'position')

    # ----------------------------------------------------------------------
    def __init__(self, settings):
        self._settings_map = dict(_base_settings_map)
        super(AXISCamera, self).__init__(settings)

        if 'color' in settings.keys():
            self.color = strtobool(settings.get("color"))
        else:
            self.color = False

        self._image_source = 'imagergb' if self.color else 'imagegrayscale'

        self._last_frame = np.zeros((1, 1))
        self._last_time = time.time()

        self._mode = 'event'
        self._eid = None
        self._frame_thread = None
        self._frame_thread_running = False
        self._stop_frame_thread = False

    # ----------------------------------------------------------------------
    def get_settings(self, option, cast, do_rotate=True, do_log=True):

        if option == 'FPSmax':
            logger.debug(f'{self._my_name}: setting {cast.__name__}({option}) requested')
            return 200
        elif option in ['pan', 'tilt', 'zoom', 'focus']:
            return super(AXISCamera, self).get_settings(option, cast, do_rotate, False)
        else:
            return super(AXISCamera, self).get_settings(option, cast, do_rotate, do_log)

    # ----------------------------------------------------------------------
    def save_settings(self, option, value):

        if option == 'FPS':
            need_restart = False
            if self._device_proxy.state() == PyTango.DevState.RUNNING:
                need_restart = True
                self._device_proxy.command_inout("StopAcquisition")
                while self._device_proxy.state() == PyTango.DevState.RUNNING:
                    time.sleep(0.1)
            super(AXISCamera, self).save_settings(option, value)
            if need_restart:
                self._device_proxy.command_inout("StartAcquisition")
        else:
            super(AXISCamera, self).save_settings(option, value)

    # ----------------------------------------------------------------------
    def _start_acquisition(self):
        """
        """

        if self._device_proxy.state() == PyTango.DevState.ON:

            logger.debug(f'{self._my_name}: starting acquisition: event mode')

            self._mode = 'event'
            self._eid = self._device_proxy.subscribe_event(self._image_source,
                                                           PyTango.EventType.CHANGE_EVENT,
                                                           self._readout_frame)

            attemp = 0
            while attemp < self.START_ATTEMPTS:
                try:
                    self._device_proxy.command_inout("StartAcquisition")
                    break
                except:
                    attemp += 1

            time.sleep(self.START_DELAY)  # ? TODO

            return True

        elif self._device_proxy.state() == PyTango.DevState.RUNNING:

            logger.debug(f'{self._my_name}: starting acquisition: thread mode')

            self._stop_frame_thread = False
            self._mode = 'attribute'
            self._frame_thread = Thread(target=self._read_frame, name='AxisCamera')
            self._frame_thread_running = True
            self._frame_thread.start()
            return True

        else:
            logger.warning("Camera should be in ON state (is it running already?)")
            return False

    # ----------------------------------------------------------------------
    def stop_acquisition(self):
        """
        """
        if self._mode == 'event':
            if self._eid is not None:
                self._device_proxy.unsubscribe_event(self._eid)
                self._eid = None
            if self._device_proxy.state() == PyTango.DevState.RUNNING:
                self._device_proxy.command_inout("StopAcquisition")
        else:
            if self._frame_thread_running:
                self._stop_frame_thread = True
                while self._frame_thread_running:
                    time.sleep(0.1)

            time.sleep(self.STOP_DELAY)  # ? TODO

    # ----------------------------------------------------------------------
    def is_running(self):
        if self._mode == 'event':
            return self._device_proxy.state() == PyTango.DevState.RUNNING
        else:
            if self._device_proxy.state() != PyTango.DevState.RUNNING:
                return False
            else:
                return self._frame_thread_running

    # ----------------------------------------------------------------------
    def _read_frame(self):
        sleep_time = self.get_settings('FPS', int)
        while not self._stop_frame_thread:
            if self._device_proxy.state() != PyTango.DevState.RUNNING:
                self._frame_thread_running = False
                raise RuntimeError('Camera was stopped!')
            try:
                self._last_frame = self._process_frame(getattr(self._device_proxy, self._image_source))
                self._new_frame_flag = True
            except Exception as err:
                logger.error('AXISCamera error: {}'.format(err))
                self.error_flag = True
                self.error_msg = str(err)
            time.sleep(1/sleep_time)
        self._frame_thread_running = False

    # ----------------------------------------------------------------------
    def _readout_frame(self, event):
        """Called each time new frame is available.
        """
        if not event.err:
            try:
                data = event.attr_value
                if data.value is not None:
                    self._last_frame = self._process_frame(data.value)
                    self._new_frame_flag = True
            except Exception as err:
                logger.error('AXISCamera error: {}'.format(err))
                self.error_flag = True
                self.error_msg = str(err)
        else:
            logger.error('AXISCamera error: {}'.format(self.error_msg))
            self.error_flag = True
            self.error_msg = event.errors

    # ----------------------------------------------------------------------
    def _process_frame(self, data):
        data = np.transpose(data)
        if self.color:
            c_data = np.zeros(data.shape + (3,), dtype=np.ubyte)
            c_data[..., 0] = data & 255
            c_data[..., 1] = (data >> 8) & 255
            c_data[..., 2] = (data >> 16) & 255

            return c_data
        else:
            return data

    # ----------------------------------------------------------------------
    def close_camera(self):
        super(AXISCamera, self).close_camera()

        if self._eid is not None:
            self._device_proxy.unsubscribe_event(self._eid)

        if self._frame_thread_running:
            self._stop_frame_thread = True
            while self._frame_thread_running:
                time.sleep(0.1)

