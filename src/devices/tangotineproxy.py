# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------


"""TangotoTine camera proxy
"""

import numpy as np
import time
from src.devices.abstract_camera import AbstractCamera

try:
    import PyTango
except ImportError:
    pass


# ----------------------------------------------------------------------
class TangoTineProxy(AbstractCamera):
    """Proxy to a physical TANGO device.
    """
    # SERVER_SETTINGS = {"PixelFormat": "Mono8",  # possibly more...
    #                    "ViewingMode": 1}

    START_DELAY = 1
    STOP_DELAY = 0.5

    _settings_map = {"RoiX": ('roi_server', "roi_x"),
                     "RoiY": ('roi_server', 'roi_y'),
                     "RoiWidth": ('roi_server', 'roi_w'),
                     "RoiHeight": ('roi_server', 'roi_h'),
                     "ExposureTime": ("settings_proxy", ("ExposureValue.Set", 'ExposureValue.Rdbk')),
                     "Gain": ("settings_proxy", ("GainValue.Set", 'GainValue.Rdbk')),
                     'max_level_limit': (None, )
                     }

    # ----------------------------------------------------------------------
    def __init__(self, beamline_id, settings, log):
        super(TangoTineProxy, self).__init__(beamline_id, settings, log)

        self._init_device()

        self._picture_size = []
        self._last_frame = np.zeros((1, 1))

        self.error_flag = False
        self.error_msg = ''

        self.period = 200
        # self._last_time = time.time()

        if not self._device_proxy.is_attribute_polled('Frame'):
            self._device_proxy.poll_attribute('Frame', self.period)

        self.self_period = not self._device_proxy.get_attribute_poll_period("Frame") == self.period

        if self.self_period:
            self._device_proxy.stop_poll_attribute("Frame")
            self._device_proxy.poll_attribute('Frame', self.period)

    # ----------------------------------------------------------------------
    def _init_device(self):
        att_conf_exposure = self._settings_proxy.get_attribute_config('ExposureValue.Set')
        att_conf_gain = self._settings_proxy.get_attribute_config('GainValue.Set')
        exposure_max = self._settings_proxy.read_attribute('ExposureValue.Max')
        exposure_min = self._settings_proxy.read_attribute('ExposureValue.Min')
        gain_max = self._settings_proxy.read_attribute('GainValue.Max')
        gain_min = self._settings_proxy.read_attribute('GainValue.Min')
        att_conf_exposure.max_value = str(exposure_max.value)
        att_conf_exposure.min_value = str(exposure_min.value)
        att_conf_gain.max_value = str(gain_max.value)
        att_conf_gain.min_value = str(gain_min.value)
        self._settings_proxy.set_attribute_config(att_conf_exposure)
        self._settings_proxy.set_attribute_config(att_conf_gain)

    # ----------------------------------------------------------------------
    def start_acquisition(self):

        self._eid = self._device_proxy.subscribe_event("Frame", PyTango.EventType.PERIODIC_EVENT, self._readout_frame)

    # ----------------------------------------------------------------------
    def stop_acquisition(self):

        self._device_proxy.unsubscribe_event(self._eid)
        self._log.debug("TangoTineTango Event unsubscribed")

    # ----------------------------------------------------------------------
    def _readout_frame(self, event):
        """Called each time new frame is available.
        """
        if not self._device_proxy:
            self._log.error("TangoTineTango DeviceProxy error")

        # for some reason this wants the 'short' attribute name, not the fully-qualified name
        # we get in event.attr_name
        data = event.device.read_attribute(event.attr_name.split('/')[6])
        if self._picture_size:
            self._last_frame = np.transpose(data.value)[self._picture_size[0]:self._picture_size[2],
                                                        self._picture_size[1]:self._picture_size[3]]
        else:
            self._last_frame = np.transpose(data.value)

        self._new_frame_flag = True

        # print('New data after {}'.format(time.time() - self._last_time))
        # self._last_time = time.time()

    # ----------------------------------------------------------------------
    def get_settings(self, option, cast):
        if option in ['wMax', 'hMax']:
            h, w = self._device_proxy.Frame.shape
            if option == 'wMax':
                return w
            else:
                return h

        elif option in ['viewW', 'viewH']:
            value = super(TangoTineProxy, self).get_settings(option, cast)
            if value == 0:
                if option == 'viewW':
                    return self.get_settings('wMax', int)
                else:
                    return self.get_settings('hMax', int)
            else:
                return value
        elif option in ['ExposureTime', 'Gain']:
            try:
                value = self._settings_proxy.read_attribute(self._settings_map[option][1][0]).value
            except:
                value = self._settings_proxy.read_attribute(self._settings_map[option][1][1]).value
                self._settings_proxy.write_attribute(self._settings_map[option][1][0], value)
            return cast(value)
        elif option == 'FPSmax':
            return 1000/self.period
        elif option == 'FPS':
            return max(1, super(TangoTineProxy, self).get_settings(option, cast))
        else:
            return super(TangoTineProxy, self).get_settings(option, cast)

    # ----------------------------------------------------------------------
    def save_settings(self, setting, value):
        if setting in ['ExposureTime', 'Gain']:
            self._settings_proxy.write_attribute(self._settings_map[setting][1][0], value)
        else:
            super(TangoTineProxy, self).save_settings(setting, value)

    # ----------------------------------------------------------------------
    def change_picture_size(self, size):

        self._picture_size = [size[0], size[1], size[0]+size[2], size[1]+size[3]]