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
    FRAME_W = 500
    FRAME_H = 500

    NOISE = 0.27

    _settings_map = {'max_width': ('self', 'FRAME_W'),
                     'max_height': ('self', 'FRAME_H')}

    visible_layouts = ('FPS', 'exposure')

    # ----------------------------------------------------------------------
    def __init__(self, settings, log):
        super(DummyProxy, self).__init__(settings, log)

        x, y = np.meshgrid(np.linspace(-4, 4, self.FRAME_H),
                           np.linspace(-4, 4, self.FRAME_W))
        x += 0.0
        y += -1.0

        mean, sigma = 0, 0.2
        self._baseData = np.exp(-((np.sqrt(x * x + y * y * 4) - mean) ** 2 / (2.0 * sigma ** 2)))
        self._data = self._baseData

        self.error_flag = False
        self.error_msg = ''

        self._fps = self.get_settings('FPS', int)
        if self._fps == 0:
            self._fps = 25

        self._generator_thread = Thread(target=self._generator)
        self._generate = False
        self._run = True
        self._new_frame_thead = Thread(target=self._new_frame)

        self._generator_thread.start()
        self._new_frame_thead.start()

        self._generator_thread_working = True
        self._new_frame_thead_working = True

    # ----------------------------------------------------------------------
    def close_camera(self):
        self._run = False
        while self._generator_thread_working or self._new_frame_thead_working:
            time.sleep(self._fps)

    # ----------------------------------------------------------------------
    def _new_frame(self):
        while self._run:
            _last_time = time.time()
            time.sleep(1 / self._fps)
            if self._generate:

                self._last_frame = self._data[self._picture_size[0]:self._picture_size[2],
                                              self._picture_size[1]:self._picture_size[3]]
                self._new_frame_flag = True
                # print('New frame after {}'.format(time.time() - _last_time))
                _last_time = time.time()

        self._new_frame_thead_working = False

    # ----------------------------------------------------------------------
    def _generator(self):
        """
        """
        while self._run:
            _last_time = time.time()
            time.sleep(1 / 10)
            if self._generate:
                nPoints = self.FRAME_W * self.FRAME_H
                self._data = self._baseData + np.random.uniform(0.0, self.NOISE, nPoints).reshape(self.FRAME_W, self.FRAME_H)
                _last_time = time.time()

        self._generator_thread_working = False

    # ----------------------------------------------------------------------
    def start_acquisition(self):
        self._generate = True
        return True

    # ----------------------------------------------------------------------
    def stop_acquisition(self):
        self._generate = False

    # ----------------------------------------------------------------------
    def get_settings(self, option, cast):
        if option == 'FPSmax':
            return 200
        elif option == 'max_width':
            return self.FRAME_W
        elif option == 'max_height':
            return self.FRAME_H
        else:
            return super(DummyProxy, self).get_settings(option, cast)

    # ----------------------------------------------------------------------
    def save_settings(self, option, value):
        if option == 'FPS':
            self._fps = value

        super(DummyProxy, self).save_settings(option, value)