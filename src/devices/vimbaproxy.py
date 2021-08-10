# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""Vimba camera proxy
"""

import time
import numpy as np

from threading import Thread
from distutils.util import strtobool

from src.devices.abstract_camera import AbstractCamera

try:
    import PyTango
except ImportError:
    pass


# ----------------------------------------------------------------------
class VimbaProxy(AbstractCamera):
    """Proxy to a physical TANGO device.
    """
    SERVER_SETTINGS = {'low': {"PixelFormat": "Mono8", "ViewingMode": 1},
                       'high': {"PixelFormat": "Mono12", "ViewingMode": 2},
                       'brhigh': {"PixelFormat": "BayerGR12", "ViewingMode": 2},
                       'bbhigh': {"PixelFormat": "BayerGB12", "ViewingMode": 2}}

    START_DELAY = 1
    STOP_DELAY = 0.5

    _settings_map = {"exposure": ("device_proxy", "ExposureTimeAbs"),
                     "gain": ["device_proxy", ""],
                     'FPSmax': ("device_proxy", "AcquisitionFrameRateLimit"),
                     'FPS': ("device_proxy", "AcquisitionFrameRateAbs"),
                     'view_x': ("device_proxy", "OffsetX"),
                     'view_y': ("device_proxy", "OffsetY"),
                     'view_h': ("device_proxy", "Height"),
                     'view_w': ("device_proxy", "Width"),
                     'max_width': ("device_proxy", "WidthMax"),
                     'max_height': ("device_proxy", "HeightMax")
                     }

    visible_layouts = ('FPS', 'exposure')

    # ----------------------------------------------------------------------
    def __init__(self, beamline_id, settings, log):
        super(VimbaProxy, self).__init__(beamline_id, settings, log)

        self._settings_map["gain"][1] = str(self._device_proxy.get_property('GainFeatureName')['GainFeatureName'][0])
        if settings.hasAttribute('high_depth'):
            self._high_depth = strtobool(settings.getAttribute("high_depth"))
        else:
            self._high_depth = False

        if self._high_depth:
            valid_formats = self._device_proxy.read_attribute('PixelFormat_Values').value
            if "Mono12" in valid_formats:
                settings = 'high'
                self._depth = 16
            elif 'BayerGR12' in valid_formats:
                settings = 'brhigh'
                self._depth = 16
            elif 'BayerGB12' in valid_formats:
                settings = 'bbhigh'
                self._depth = 16
            else:
                raise RuntimeError('Unknown pixel format')
        else:
            settings = 'low'
            self._depth = 8

        self.error_msg = ''
        self.error_flag = False
        self._last_frame = np.zeros((1, 1))
        self._last_time = time.time()

        self._mode = None
        self._eid = None
        self._frame_thread = None
        self._frame_thread_running = False
        self._stop_frame_thread = False

        if self._device_proxy.state() == PyTango.DevState.RUNNING:
            self._device_proxy.StopAcquisition()

        for k, v in self.SERVER_SETTINGS[settings].items():
            self._device_proxy.write_attribute(k, v)

    # ----------------------------------------------------------------------
    def get_settings(self, option, cast):
        if option == 'max_level_limit':
            if self._high_depth:
                return 2 ** 12
            else:
                return 2 ** 8
        else:
            return super(VimbaProxy, self).get_settings(option, cast)

    # ----------------------------------------------------------------------
    def start_acquisition(self):
        """
        """

        if self._device_proxy.state() == PyTango.DevState.ON:
            self._mode = 'event'
            self._eid = self._device_proxy.subscribe_event("Image{:d}".format(self._depth),
                                                           PyTango.EventType.DATA_READY_EVENT,
                                                           self._readout_frame, [], True)

            self._device_proxy.command_inout("StartAcquisition")
            time.sleep(self.START_DELAY)  # ? TODO

            return True
        elif self._device_proxy.state() == PyTango.DevState.MOVING:
            self._mode = 'attribute'
            self._frame_thread = Thread(target=self._read_frame)
            self._frame_thread_running = True
            self._frame_thread.start()
            return True
        else:
            self._log.warning("Camera should be in ON state (is it running already?)")
            return False

    # ----------------------------------------------------------------------
    def stop_acquisition(self):
        """
        """
        if self._mode == 'event':
            if self._eid is not None:
                self._device_proxy.unsubscribe_event(self._eid)
                self._eid = None
            if self._device_proxy.state() == PyTango.DevState.MOVING:
                self._device_proxy.command_inout("StopAcquisition")
        else:
            if self._frame_thread_running:
                self._stop_frame_thread = True
                while self._frame_thread_running:
                    time.sleep(0.1)

            time.sleep(self.STOP_DELAY)  # ? TODO

    # ----------------------------------------------------------------------
    def is_running(self):
        return self._device_proxy.state() == PyTango.DevState.MOVING

    # ----------------------------------------------------------------------
    def _read_frame(self):
        sleep_time = self.get_settings('FPS', int)
        while not self._stop_frame_thread:
            try:
                self._last_frame = np.transpose(getattr(self._device_proxy, "Image{:d}".format(self._depth)))
                self._new_frame_flag = True
            except Exception as err:
                self._log.error('Vimba error: {}'.format(err))
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
                data = event.device.read_attribute(event.attr_name.split('/')[6])
                self._last_frame = np.transpose(data.value)
                self._new_frame_flag = True

            except Exception as err:
                self._log.error('Vimba error: {}'.format(err))
                self.error_flag = True
                self.error_msg = str(err)
        else:
            self._log.error('Vimba error: {}'.format(self.error_msg))
            self.error_flag = True
            self.error_msg = event.errors

    # ----------------------------------------------------------------------
    def close_camera(self):
        super(VimbaProxy, self).close_camera()

        if self._eid is not None:
            self._device_proxy.unsubscribe_event(self._eid)

        if self._frame_thread_running:
            self._stop_frame_thread = True
            while self._frame_thread_running:
                time.sleep(0.1)

