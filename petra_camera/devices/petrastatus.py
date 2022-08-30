# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""Dummy 2D data generator.
"""
import threading
import time
import requests
from random import random
import io
from PIL import Image
import numpy as np
import logging
import PyTango

from threading import Thread

from petra_camera.devices.base_camera import BaseCamera
from petra_camera.main_window import APP_NAME

logger = logging.getLogger(APP_NAME)

DEFAULT_TANGO_SERVER = 'haso102m:10000/pxx/petrastatusscreen/all'


# ----------------------------------------------------------------------
class PetraStatus(BaseCamera):
    """
    """
    _settings_map = {'max_width': ('self', 'FRAME_W'),
                     'max_height': ('self', 'FRAME_H')}

    visible_layouts = ('FPS')

    FRAME_W = 1122
    FRAME_H = 898

    # ----------------------------------------------------------------------
    def __init__(self, settings):
        super(PetraStatus, self).__init__(settings)

        self._fps = self.get_settings('FPS', int)
        if self._fps == 0:
            self._fps = 1

        if 'status_source' in settings.keys():
            self._mode = settings.get("status_source")
        else:
            self._mode = 'tango'

        if self._mode == 'tango' and 'server' in settings.keys():
            self._tango_server = settings.get("server")
        else:
            self._tango_server = DEFAULT_TANGO_SERVER

        if self._mode != 'tango':
            self.FRAME_W = 800
            self.FRAME_H = 600

        self._picture_thread = Thread(target=self._readout_frame)
        self._generator_thread_working = False
        self._stop_picture_thread = threading.Event()
        self._run_acquisition = threading.Event()
        self._picture_thread.start()

    # ----------------------------------------------------------------------
    def close_camera(self):

        self._stop_picture_thread.set()
        while self._generator_thread_working:
            time.sleep(1/self._fps)

    # ----------------------------------------------------------------------
    def _readout_frame(self):

        while not self._stop_picture_thread.is_set():

            time.sleep(1 / self._fps)

            if self._run_acquisition.is_set():
                try:
                    if self._mode == 'tango':
                        data = PyTango.DeviceProxy(self._tango_server).statusscreen[
                               self._picture_size[0]:self._picture_size[2], self._picture_size[1]:self._picture_size[3]]
                        c_data = np.zeros(data.shape + (3,), dtype=np.ubyte)
                        c_data[..., 0] = data & 255
                        c_data[..., 1] = (data >> 8) & 255
                        c_data[..., 2] = (data >> 16) & 255
                        self._last_frame = c_data
                        self._last_camera_msg = PyTango.DeviceProxy(self._tango_server).laststatusmessage
                        self._new_frame_flag = True
                        self._new_msg_flag = True
                        logger.debug(f"{self._my_name} new frame")
                    else:
                        ans = requests.get(f'https://winweb.desy.de/mca/accstatus/infoscreen/petra_status_800.png?{random()}')
                        if ans.status_code == 200:
                            picture_stream = io.BytesIO(ans.content)
                            picture = Image.open(picture_stream)
                            frame = np.rot90(np.asarray(picture, dtype=np.int32), 1)[::-1, :]
                            self._last_frame = frame[self._picture_size[0]: self._picture_size[2],
                                                     self._picture_size[1]: self._picture_size[3]]
                            self._new_frame_flag = True
                            logger.debug(f"{self._my_name} new frame")
                except Exception as err:
                    logger.error(f"{self._my_name}: cannot get new frame: {repr(err)}")

        self._generator_thread_working = False

    # ----------------------------------------------------------------------
    def _start_acquisition(self):

        logger.debug(f"{self._my_name} starting thread")

        self._run_acquisition.set()
        return True

    # ----------------------------------------------------------------------
    def stop_acquisition(self):
        self._run_acquisition.clear()

    # ----------------------------------------------------------------------
    def is_running(self):

        return self._run_acquisition.is_set()

    # ----------------------------------------------------------------------
    def get_settings(self, option, cast, do_rotate=True, do_log=True):

        if option in ['FPSmax', 'max_width', 'max_height']:

            logger.debug(f'{self._my_name}: setting {cast.__name__}({option}) requested')

            if option == 'FPSmax':
                return 200
            elif option == 'max_width':
                return self.FRAME_W
            elif option == 'max_height':
                return self.FRAME_H
        else:
            return super(PetraStatus, self).get_settings(option, cast, do_rotate, do_log)

    # ----------------------------------------------------------------------
    def save_settings(self, option, value):

        if option == 'FPS':

            logger.debug(f'{self._my_name}: setting {option}: new value {value}')
            self._fps = value

        super(PetraStatus, self).save_settings(option, value)