# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""Vimba camera proxy
"""

import time
import numpy as np
import logging
import tango

from threading import Thread
from distutils.util import strtobool

from petra_camera.devices.base_camera import BaseCamera

from petra_camera.constants import APP_NAME
logger = logging.getLogger(APP_NAME)

_base_settings_map = {"exposure": ("device_proxy", "ExposureTimeAbs"),
                      # "gain": ["device_proxy", "Gain"],
                      'FPSmax': ("device_proxy", "AcquisitionFrameRateLimit"),
                      'FPS': ("device_proxy", "AcquisitionFrameRateAbs"),
                      'view_x': ("device_proxy", "OffsetX"),
                      'view_y': ("device_proxy", "OffsetY"),
                      'view_h': ("device_proxy", "Height"),
                      'view_w': ("device_proxy", "Width"),
                      'max_width': ("device_proxy", "WidthMax"),
                      'max_height': ("device_proxy", "HeightMax")
                      }

# ----------------------------------------------------------------------
class TangoVimba(BaseCamera):
    """Proxy to a physical TANGO device.
    """
    SERVER_SETTINGS = {'bw':    {'low': [1, 'Image8'],
                                 'high': [2, 'Image16']},
                       'color': {'low': [5, 'ImageRGB'],
                                 'high': [5, 'ImageRGB']}
                       }

    PIXEL_FORMATS = {'color': {'high': [],
                               'low': ['RGB8Packed']},
                     'bw':    {'high': ["Mono12", "BayerGR12", "BayerRG12", "BayerGB12"],
                               'low': ['Mono8']}
                     }

    START_DELAY = 1
    STOP_DELAY = 0.5

    START_ATTEMPTS = 2

    visible_layouts = ('FPS', 'exposure')

    # ----------------------------------------------------------------------
    def __init__(self, settings):
        self._settings_map = dict(_base_settings_map)
        if 'roi_server' in settings.keys():
            self._settings_map.update({"counter_x": ('roi_server', 'roi_x'),
                                       "counter_y": ('roi_server', 'roi_y'),
                                       "counter_w": ('roi_server', 'roi_w'),
                                       "counter_h": ('roi_server', 'roi_h')})
            self.counter_source = '_roi_server'
            self.counter_name = 'value_parameter'

        super(TangoVimba, self).__init__(settings)

        self._settings_map["gain"] = ("device_proxy", str(self._device_proxy.get_property('GainFeatureName')['GainFeatureName'][0]))
        if 'high_depth' in settings.keys():
            high_depth = strtobool(settings.get("high_depth"))
        else:
            high_depth = False

        if 'color' in settings.keys():
            color = strtobool(settings.get("color"))
        else:
            color = False

        accepted_format = None

        if self._device_proxy.state() != tango.DevState.MOVING:
            valid_formats = self._device_proxy.read_attribute('PixelFormat_Values').value
        else:
            valid_formats = self._device_proxy.pixelformat
        if color:
            if high_depth:
                for pixel_format in self.PIXEL_FORMATS['color']['high']:
                    if pixel_format in valid_formats:
                        accepted_format = pixel_format
                        self._high_depth = True
                        self._color = True
            if accepted_format is None:
                for pixel_format in self.PIXEL_FORMATS['color']['low']:
                    if pixel_format in valid_formats:
                        accepted_format = pixel_format
                        self._high_depth = False
                        self._color = True

        if accepted_format is None:
            if high_depth:
                for pixel_format in self.PIXEL_FORMATS['bw']['high']:
                    if pixel_format in valid_formats:
                        accepted_format = pixel_format
                        self._high_depth = True
                        self._color = False
            if accepted_format is None:
                for pixel_format in self.PIXEL_FORMATS['bw']['low']:
                    if pixel_format in valid_formats:
                        accepted_format = pixel_format
                        self._high_depth = False
                        self._color = False

        if accepted_format is None:
            raise RuntimeError('Cannot find acceptable pixel format!')

        if self._device_proxy.state() != tango.DevState.MOVING:
            self._device_proxy.pixelformat = accepted_format
            self._device_proxy.viewingmode = \
            self.SERVER_SETTINGS['color' if self._color else 'bw']['high' if self._high_depth else 'low'][0]

        self._image_source = \
            self.SERVER_SETTINGS['color' if self._color else 'bw']['high' if self._high_depth else 'low'][1]

        self._last_frame = np.zeros((1, 1))
        self._last_time = time.time()

        self._mode = 'event'
        self._eid = None
        self._frame_thread = None
        self._frame_thread_running = False
        self._stop_frame_thread = False

        self._start_errors_received = False

    # ----------------------------------------------------------------------
    def get_settings(self, option, cast, do_rotate=True, do_log=True):

        if option == 'max_level_limit':

            logger.debug(f'{self._my_name}: setting {cast.__name__}({option}) requested')

            if self._high_depth:
                return 2 ** 12
            else:
                return 2 ** 8

        elif option == 'exposure':
            return super(TangoVimba, self).get_settings(option, cast, do_rotate, do_log) / 1000

        else:
            return super(TangoVimba, self).get_settings(option, cast, do_rotate, do_log)

    # ----------------------------------------------------------------------
    def save_settings(self, option, value):

        if option == 'exposure':
            super(TangoVimba, self).save_settings(option, value * 1000)
        else:
            super(TangoVimba, self).save_settings(option, value)

    # ----------------------------------------------------------------------
    def _start_acquisition(self):
        """
        """

        if self._device_proxy.state() not in [tango.DevState.ON, tango.DevState.MOVING]:
            logger.warning("Camera should be in ON state (is it running already?)")
            return False

        event_mode = self._device_proxy.state() == tango.DevState.ON

        logger.debug(f'{self._my_name}: starting acquisition from {self._image_source}, mode: {"event" if event_mode else "thread"}')

        if event_mode:

            self._start_errors_received = False

            self._mode = 'event'
            self._eid = self._device_proxy.subscribe_event(self._image_source,
                                                           tango.EventType.CHANGE_EVENT,
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
        else:

            self._stop_frame_thread = False
            self._mode = 'attribute'
            self._frame_thread = Thread(target=self._read_frame)
            self._frame_thread_running = True
            self._frame_thread.start()
            return True

    # ----------------------------------------------------------------------
    def stop_acquisition(self):
        """
        """
        if self._mode == 'event':
            if self._eid is not None:
                self._device_proxy.unsubscribe_event(self._eid)
                self._eid = None
            if self._device_proxy.state() == tango.DevState.MOVING:
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
            return self._device_proxy.state() == tango.DevState.MOVING
        else:
            if self._device_proxy.state() != tango.DevState.MOVING:
                return False
            else:
                return self._frame_thread_running

    # ----------------------------------------------------------------------
    def _read_frame(self):
        sleep_time = self.get_settings('FPS', int)
        while not self._stop_frame_thread:
            if self._device_proxy.state() != tango.DevState.MOVING:
                self._frame_thread_running = False
                raise RuntimeError('Camera was stopped!')
            try:
                self._last_frame = self._process_frame(getattr(self._device_proxy, self._image_source))
                self._new_frame_flag = True
            except Exception as err:
                logger.error(f'{self._my_name}: error: {err}', exc_info=True)
                self.error_flag = True
                self.error_msg = str(err)
            time.sleep(1/sleep_time)
        self._frame_thread_running = False

    # ----------------------------------------------------------------------
    def _readout_frame(self, event):
        """Called each time new frame is available.
        """
        self.error_flag = False
        self.error_msg = ""
        if not event.err:
            try:
                data = event.attr_value
                if data.quality == tango.AttrQuality.ATTR_VALID:
                    self._last_frame = self._process_frame(data.value)
                    self._new_frame_flag = True
                    return
                else:
                    err = f"{self._my_name} error: AttrQuality is {data.quality}"
            except Exception as err:
                pass
        else:
            err = event.errors
        if self._start_errors_received:
            self.error_flag = True
            self.error_msg = str(err)
            logger.error(f'{self._my_name} error: {err}', exc_info=True)
        else:
            self._start_errors_received = True
            logger.error(f'{self._my_name} Startup error: {err}', exc_info=True)

    # ----------------------------------------------------------------------
    def _process_frame(self, data):
        data = np.transpose(data)
        if self._color:
            c_data = np.zeros(data.shape + (3,), dtype=np.ubyte)
            c_data[..., 0] = data & 255
            c_data[..., 1] = (data >> 8) & 255
            c_data[..., 2] = (data >> 16) & 255

            return c_data
        else:
            return data

    # ----------------------------------------------------------------------
    def close_camera(self):
        super(TangoVimba, self).close_camera()

        if self._eid is not None:
            self._device_proxy.unsubscribe_event(self._eid)

        if self._frame_thread_running:
            self._stop_frame_thread = True
            while self._frame_thread_running:
                time.sleep(0.1)

