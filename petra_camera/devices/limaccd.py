# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------


"""TangotoTine camera proxy
"""

import numpy as np
import time
import logging
import HasyUtils as hu
from threading import Thread
import tango

from petra_camera.devices.base_camera import BaseCamera

from petra_camera.constants import APP_NAME
logger = logging.getLogger(APP_NAME)

_base_settings_map = {
    "exposure": ("device_proxy", "video_exposure"),
    "gain": ("device_proxy", "video_gain"),
    'max_width': ("device_proxy", "image_width"),
    'max_height': ("device_proxy", "image_height")
}


# ----------------------------------------------------------------------
class LimaCCD(BaseCamera):
    """Proxy to a physical TANGO device.
    """
    # SERVER_SETTINGS = {"PixelFormat": "Mono8",  # possibly more...
    #                    "ViewingMode": 1}

    visible_layouts = ('exposure',)

    # ----------------------------------------------------------------------
    def __init__(self, settings):
        self._settings_map = dict(_base_settings_map)
        super(LimaCCD, self).__init__(settings)

        # TODO: super ugly patch, needed more proper solution:
        db = self._device_proxy.get_device_db()
        server = db.get_device_info(self._device_proxy.name()).ds_full_name
        devices = db.get_device_class_list(server).value_string

        def pairs(lst):
            a = iter(lst)
            return list(zip(a, a))

        for device_name, class_name in pairs(devices):
            if class_name == "LiveViewer":
                self._image_source = tango.DeviceProxy(db.get_db_host().split('.')[0] + ':' + db.get_db_port() + "/" + device_name)
                break

        self._last_frame = np.zeros((1, 1))

        self.period = 0.1

        self._camera_read_thread = None
        self._camera_read_thread_running = False

    # ----------------------------------------------------------------------
    def _start_acquisition(self):
        """
        start acquisition tread
        :return: bool
        """

        logger.debug(f"{self._my_name} starting thread")

        try:
            self._camera_read_thread = Thread(target=self._readout_frame)
            self._camera_read_thread_running = True
            self._camera_read_thread.start()

            return True

        except Exception as err:

            logger.exception(err)

        return False

    # ----------------------------------------------------------------------
    def stop_acquisition(self):
        """
        stops acquisition tread
        :return:
        """

        if self._camera_read_thread_running:
            self._camera_read_thread_running = False
            self._camera_read_thread.join()

        logger.debug(f"{self._my_name} thread stopped")

    # ----------------------------------------------------------------------
    def is_running(self):
        """

        :return: bool
        """
        return self._camera_read_thread_running

    # ----------------------------------------------------------------------
    def _readout_frame(self):
        """Called each time new frame is available.
        """
        if not self._device_proxy.video_active:
            self._device_proxy.video_active = True

        last_counter = self._device_proxy.video_last_image_counter
        self._device_proxy.video_live = True

        while self._camera_read_thread_running:
            if self._device_proxy.video_last_image_counter != last_counter:
                last_counter = self._device_proxy.video_last_image_counter
                try:
                    self._last_frame = self._image_source.image[self._picture_size[0]:self._picture_size[2],
                                                                self._picture_size[1]:self._picture_size[3]]
                    self._new_frame_flag = True
                    logger.debug(f"{self._my_name} new frame")

                    time.sleep(self.period)

                except Exception as err:

                    logger.exception(f"{self._my_name} exception during new frame: {err}")
                    self._camera_read_thread_running = False

        self._device_proxy.video_live = True

    # ----------------------------------------------------------------------
    def get_settings(self, option, cast, do_rotate=True, do_log=True):
        """
        here we catch some settings before read them from general settings
        :param option:
        :param cast:
        :return:
        """

        # if option in ['max_width', 'max_height', 'FPSmax']:
        #
        #     logger.debug(f'{self._my_name}: setting {cast.__name__}({option}) requested')
        #
        #     if option in ['max_width', 'max_height']:
        #
        #         if self._frame_size is None:
        #             w, h = self._device_proxy.Frame.shape
        #         else:
        #             w, h = self._frame_size
        #
        #         if option == 'max_width':
        #             return w
        #         else:
        #             return h
        #
        #     elif option == 'FPSmax':
        #         return 1000/self.period
        #
        # elif option == 'FPS':
        #     return max(1, super(LimaCCD, self).get_settings(option, cast, do_rotate, do_log))
        #
        # else:
        return super(LimaCCD, self).get_settings(option, cast, do_rotate, do_log)