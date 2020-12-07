# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""Dummy 2D data generator.
"""

import numpy as np
from abstract_camera import AbstractCamera
from threading import Thread
import time

# ----------------------------------------------------------------------
class DummyProxy(AbstractCamera):
    """
    """
    FRAME_W = 2500
    FRAME_H = 2500

    NOISE = 0.27

    _settings_map = {}

    # ----------------------------------------------------------------------
    def __init__(self, beamline_id, settings, log):
        super(DummyProxy, self).__init__(beamline_id, settings, log)

        self._picture_size = [0, 0, self.FRAME_W, self.FRAME_H]

        x, y = np.meshgrid(np.linspace(-4, 4, self.FRAME_H),
                           np.linspace(-4, 4, self.FRAME_W))
        x += 0.0
        y += -1.0

        mean, sigma = 0, 0.2
        self._baseData = np.exp(-((np.sqrt(x * x + y * y * 4) - mean) ** 2 / (2.0 * sigma ** 2)))
        self._data = self._baseData

        self.error_flag = False
        self.error_msg = ''

        self._fps = 25

        self._generator_thread = Thread(target=self._generator)
        self._generate = False

        self._new_frame_thead = Thread(target=self._new_frame)
    
    # ----------------------------------------------------------------------
    def _new_frame(self):
        _last_time = time.time()
        while self._generate:
            time.sleep(1/self._fps)
            self._last_frame = self._data[self._picture_size[0]:self._picture_size[2],
                                    self._picture_size[1]:self._picture_size[3]]
            self._new_frame_flag = True
            # print('New frame after {}'.format(time.time() - _last_time))
            _last_time = time.time()

    # ----------------------------------------------------------------------
    def _generator(self):
        """
        """
        _last_time = time.time()
        while self._generate:
            time.sleep(1/10)
            nPoints = self.FRAME_W * self.FRAME_H
            self._data = self._baseData + np.random.uniform(0.0, self.NOISE, nPoints).reshape(self.FRAME_W, self.FRAME_H)
            _last_time = time.time()

    # ----------------------------------------------------------------------
    def start_acquisition(self):
        self._generate = True
        self._generator_thread.start()
        self._new_frame_thead.start()
        return True

    # ----------------------------------------------------------------------
    def stop_acquisition(self):
        self._generate = False

    # ----------------------------------------------------------------------
    def get_settings(self, option, cast):
        if option == 'FPSmax':
            return 200
        elif option == 'FPS':
            return self._fps
        elif option == 'wMax':
            return self.FRAME_W
        elif option == 'hMax':
            return self.FRAME_H
        else:
            return super(DummyProxy, self).get_settings(option, cast)

    # ----------------------------------------------------------------------
    def save_settings(self, option, value):
        if option == 'FPS':
            self._fps = value
        else:
            super(DummyProxy, self).save_settings(option, value)

    # ----------------------------------------------------------------------
    def change_picture_size(self, size):

        self._picture_size = [size[0], size[1], size[0]+size[2], size[1]+size[3]]
