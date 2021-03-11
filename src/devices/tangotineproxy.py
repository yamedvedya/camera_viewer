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
                     "exposure": ("device_proxy", "Exposure"),
                     "gain": ("device_proxy", "Gain"),
                     'max_level_limit': (None, ),
                     "counter_x": ('roi_server', 'roi_x'),
                     "counter_y": ('roi_server', 'roi_y'),
                     "counter_w": ('roi_server', 'roi_w'),
                     "counter_h": ('roi_server', 'roi_h'),
                     }

    visible_layouts = ('FPS', 'exposure')

    # ----------------------------------------------------------------------
    def __init__(self, beamline_id, settings, log):
        super(TangoTineProxy, self).__init__(beamline_id, settings, log)

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

        return True

    # ----------------------------------------------------------------------
    def stop_acquisition(self):

        if self._camera_read_thread_running:
            self._camera_read_thread_running = False
            self._camera_read_thread.join()

        self._log.debug("TangoTineTango thread stoppped")

    # ----------------------------------------------------------------------
    def _readout_frame(self):
        """Called each time new frame is available.
        """

        while self._camera_read_thread_running:
            try:
                self._last_frame = self._device_proxy.Frame[self._picture_size[0]:self._picture_size[2],
                                                            self._picture_size[1]:self._picture_size[3]]
                self._new_frame_flag = True
                time.sleep(self.period)
            except:
                self._camera_read_thread_running = False

    # ----------------------------------------------------------------------
    def get_settings(self, option, cast):
        if option in ['max_width', 'max_height']:
            w, h = self._device_proxy.Frame.shape
            if option == 'max_width':
                return w
            else:
                return h

        elif option == 'FPSmax':
            return 1000/self.period

        elif option == 'FPS':
            return max(1, super(TangoTineProxy, self).get_settings(option, cast))
        else:
            return super(TangoTineProxy, self).get_settings(option, cast)