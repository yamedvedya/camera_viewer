# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------


"""TangotoTine camera proxy
"""

import numpy as np
import time
from threading import Thread
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

    _settings_map = {
                     "exposure": ("settings_proxy", ("ExposureValue.Set", 'ExposureValue.Rdbk')),
                     "gain": ("settings_proxy", ("GainValue.Set", 'GainValue.Rdbk')),
                     'max_level_limit': (None, )
                     }

    visible_layouts = ('FPS', 'exposure')

    # ----------------------------------------------------------------------
    def __init__(self, beamline_id, settings, log):
        super(TangoTineProxy, self).__init__(beamline_id, settings, log)

        if self._settings_proxy is not None:
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

        self._last_frame = np.zeros((1, 1))

        self.error_flag = False
        self.error_msg = ''

        self.period = 1/self.get_settings('FPS', int)

        self._camera_read_thread = None
        self._camera_read_thread_running = False

    # ----------------------------------------------------------------------
    def start_acquisition(self):

        self._camera_read_thread = Thread(target=self._readout_frame)
        self._camera_read_thread_running = True
        self._camera_read_thread.start()


    # ----------------------------------------------------------------------
    def stop_acquisition(self):

        if self._camera_read_thread_running:
            self._camera_read_thread_running = False
            self._camera_read_thread.join()

        self._log.debug("TangoTineTango thread stoppped")

    # ----------------------------------------------------------------------
    def _readout_frame(self, event):
        """Called each time new frame is available.
        """

        while self._camera_read_thread_running:
            try:
                self._last_frame = self._device_proxy.Frame
                self._new_frame_flag = True
                time.sleep(self.period)
            except:
                self._camera_read_thread_running = False

    # ----------------------------------------------------------------------
    def get_settings(self, option, cast):
        if option in ['max_width', 'max_height']:
            h, w = self._device_proxy.Frame.shape
            if option == 'max_width':
                return w
            else:
                return h

        elif option in ['ExposureTime', 'Gain']:
            if self._settings_proxy is not None:
                try:
                    value = self._settings_proxy.read_attribute(self._settings_map[option][1][0]).value
                except:
                    value = self._settings_proxy.read_attribute(self._settings_map[option][1][1]).value
                    self._settings_proxy.write_attribute(self._settings_map[option][1][0], value)
                return cast(value)
            else:
                return None

        elif option == 'FPSmax':
            return 1000/self.period

        elif option == 'FPS':
            return max(1, super(TangoTineProxy, self).get_settings(option, cast))
        else:
            return super(TangoTineProxy, self).get_settings(option, cast)

    # ----------------------------------------------------------------------
    def save_settings(self, setting, value):
        if setting in ['ExposureTime', 'Gain']:
            if self._settings_proxy is not None:
                self._settings_proxy.write_attribute(self._settings_map[setting][1][0], value)
        else:
            super(TangoTineProxy, self).save_settings(setting, value)