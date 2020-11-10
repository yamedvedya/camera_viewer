# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------


"""TangotoTine camera proxy
"""

import numpy as np
from abstract_camera import AbstractCamera

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
                     "Exposure": ("settings_proxy", ("ExposureValue.Set", 'ExposureValue.Default')),
                     "Gain": ("settings_proxy", ("ExposureValue.Set", 'GainValue.Default')),
                     'FPS': (None, ),
                     'wMax': (None, ),
                     'hMax': (None, ),
                     'viewX': (None, ),
                     'viewY': (None, ),
                     'viewW': (None, ),
                     'viewH': (None, )
                     }

    # ----------------------------------------------------------------------
    def __init__(self, beamline_id, settings, log):
        super(TangoTineProxy, self).__init__(beamline_id, settings, log)

        self._init_device()

        self._new_flag = False
        self.error_flag = False
        self.error_msg = ''
        self._last_frame = np.zeros((1, 1))
        self.period = 200
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

    # ----------------------------------------------------------------------
    def _readout_frame(self, event):
        """Called each time new frame is available.
        """
        if not self._device_proxy:
            self._log.error("TangoTineTango DeviceProxy error")

        # for some reason this wants the 'short' attribute name, not the fully-qualified name
        # we get in event.attr_name
        data = event.device.read_attribute(event.attr_name.split('/')[6])
        self._last_frame = np.transpose(data.value)
        self._new_flag = True