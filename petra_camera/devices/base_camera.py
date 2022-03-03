# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
Base camera class
"""

import PyTango
import logging
import time
import numpy as np

from PyQt5 import QtCore
from distutils.util import strtobool

from petra_camera.devices.screen_motor import MotorExecutor

from petra_camera.main_window import APP_NAME

logger = logging.getLogger(APP_NAME)


# ----------------------------------------------------------------------
class BaseCamera(object):

    counter_source = '_roi_server'
    counter_name = 'scan_parameter'

    # ----------------------------------------------------------------------
    def __init__(self, settings):
        """
        """
        super(BaseCamera, self).__init__()

        self._settings = settings

        self.file_name = ''

        self._frame_size = None

        self._new_frame_flag = False
        self._eid = None  # Tango even ID

        self._my_name = settings.get("name")

        # picture rotate and flip properties
        if 'flip_vertical' in settings.keys():
            self.flip_v = bool(strtobool(settings.get("flip_vertical")))
        else:
            self.flip_v = False

        if 'flip_horizontal' in settings.keys():
            self.flip_h = bool(strtobool(settings.get("flip_horizontal")))
        else:
            self.flip_h = False

        if 'rotate' in settings.keys():
            self.rotate_angle = int(settings.get("rotate")) % 4
        else:
            self.rotate_angle = 0

        # DeviceProxies instances
        if 'tango_server' in settings.keys():
            name = str(settings.get("tango_server"))
            self._device_proxy = PyTango.DeviceProxy(name)
            if self._device_proxy.state() == PyTango.DevState.FAULT:
                raise RuntimeError(f'{name} in FAULT state!')
            logger.debug(f'{self._my_name}: new tango proxy {name}')
        else:
            self._device_proxy = None

        if 'settings_server' in settings.keys():
            name = str(settings.get("settings_server"))
            self._settings_proxy = PyTango.DeviceProxy(name)
            if self._settings_proxy.state() == PyTango.DevState.FAULT:
                raise RuntimeError(f'{name} in FAULT state!')
            logger.debug(f'{self._my_name}: new settings proxy {name}')
        else:
            self._settings_proxy = None

        if 'roi_server' in settings.keys():
            name = str(settings.get("roi_server"))
            self._roi_server = PyTango.DeviceProxy(name)
            if self._roi_server.state() == PyTango.DevState.FAULT:
                raise RuntimeError(f'{name} in FAULT state!')
            logger.debug(f'{self._my_name}: new roi server {name}')
        else:
            self._roi_server = None

        # if camera has a screen control
        if 'motor_type' in settings.keys() and \
                (str(settings.get("motor_type")).lower() not in ['none', 'no', '']):
            self._motor_worker = MotorExecutor(settings)
        else:
            self._motor_worker = None

        # for high resolution cameras to decrease CPU load
        self.reduce_resolution = max(self.get_settings('Reduce', int), 1)

        size_x = self.get_settings('view_x', int)
        size_y = self.get_settings('view_y', int)
        size_w = self.get_settings('view_w', int)
        size_h = self.get_settings('view_h', int)

        self._picture_size = [size_x, size_y, size_x + size_w, size_y + size_h]

    # ----------------------------------------------------------------------
    def close_camera(self):
        """
        save camera close
        :return:
        """
        if self._motor_worker is not None:
            self._motor_worker.stop()

    # ----------------------------------------------------------------------
    def start_acquisition(self):
        raise RuntimeError('Not implemented')

    # ----------------------------------------------------------------------
    def stop_acquisition(self):
        raise RuntimeError('Not implemented')

    # ----------------------------------------------------------------------
    # ------------------------ Frame functionality -------------------------
    # ----------------------------------------------------------------------
    def maybe_read_frame(self):
        """

        :return: None if no new picture or 2d np.array if there is a new frame
        """
        if not self._new_frame_flag:
            return None

        self._new_frame_flag = False
        return self.rotate()

    # ----------------------------------------------------------------------
    def rotate(self):
        """
        rotate and flip picture
        :return: 2d np.array
        """

        if self.flip_v and self.flip_h:
            self._last_frame = self._last_frame[::-1, ::-1]
        elif self.flip_v:
            self._last_frame = self._last_frame[::, ::-1]
        elif self.flip_h:
            self._last_frame = self._last_frame[::-1, :]

        if self.rotate_angle:
            self._last_frame = np.rot90(self._last_frame, self.rotate_angle)

        return self._last_frame[::self.reduce_resolution, ::self.reduce_resolution]

    # ----------------------------------------------------------------------
    def is_running(self):
        """

        :return: bool
        """
        return True

    # ----------------------------------------------------------------------
    # ------------------------- Picture clip/resolution  -------------------
    # ----------------------------------------------------------------------
    def _get_frame_size(self):
        if self._frame_size is None:
            self._frame_size = self.get_settings('max_width', int), self.get_settings('max_height', int)

        return self._frame_size

    # ----------------------------------------------------------------------
    def set_picture_clip(self, size):
        """
        sets picture clip

        :param size: (x, y, w, h) - parameters of picture clip
        :return: None
        """

        self._picture_size = [size[0], size[1], size[0]+size[2], size[1]+size[3]]

        self.save_settings('view_x', size[0])
        self.save_settings('view_y', size[1])
        self.save_settings('view_w', size[2])
        self.save_settings('view_h', size[3])

        self._frame_size = size[2], size[3]

    # ----------------------------------------------------------------------
    def get_picture_clip(self):
        """

        :return: (x, y, w, h) - parameters of picture clip
        """

        return [self._picture_size[0], self._picture_size[1],
                self._picture_size[2] - self._picture_size[0],
                self._picture_size[3] - self._picture_size[1]]

    # ----------------------------------------------------------------------
    def get_reduction(self):
        """

        :return: int, picture reduction
        """
        return self.reduce_resolution

    # ----------------------------------------------------------------------
    def set_reduction(self, value):
        """
        sets picture reduction

        :param value: int,
        :return:
        """
        self.save_settings('Reduce', value)
        self.reduce_resolution = value

    # ----------------------------------------------------------------------
    # ------------------------ Camera settings load/save -------------------
    # ----------------------------------------------------------------------
    def get_settings(self, option, cast, do_rotate=True):
        """
         reads the requested setting according the settings map

        :param option: str, setting name
        :param cast:
        :return: None, of False (if cast == bool), '' (is cast == str) if there is no such settings,
                 or cast(requested setting)
        """

        _start_time = time.time()

        if option in self._settings_map.keys():
            try:
                if self._settings_map[option][0] == 'roi_server' and self._roi_server is not None:
                    value = getattr(self._roi_server, self._settings_map[option][1])

                elif self._settings_map[option][0] == 'settings_proxy' and self._settings_proxy is not None:
                    value = self._settings_proxy.read_attribute(self._settings_map[option][1]).value

                elif self._settings_map[option][0] == 'device_proxy' and self._device_proxy is not None:
                    value = self._device_proxy.read_attribute(self._settings_map[option][1]).value

                elif self._settings_map[option][0] == 'self':
                    value = getattr(self, self._settings_map[option][1])

                elif self._settings_map[option][0] is None:
                    value = None
                else:
                    raise RuntimeError('Unknown setting source')
            except:
                value = None

        else:
            try:
                value = QtCore.QSettings(APP_NAME).value("{}/{}".format(self._my_name, option))
            except:
                value = None

        if option in ['view_w', 'view_h']:
            if value is None or int(value) < 1:
                if option == 'view_w':
                    return self.get_settings('max_width', int) - self.get_settings('view_x', int)
                else:
                    return self.get_settings('max_height', int) - self.get_settings('view_y', int)

        if value is not None:
            if cast == bool:
                try:
                    value = strtobool(str(value))
                except:
                    print('Cannot convert settings {} {} to bool'.format(option, value))
                    value = False
            elif cast == int:
                value = int(float(value))
            else:
                value = cast(value)

        else:
            if cast == bool:
                value = False
            elif cast in [int, float]:
                value = cast(0)
            elif cast == str:
                value = ''
            else:
                value = None

        if do_rotate and option in ["counter_x", "counter_y", "counter_w", "counter_h"]:

            value = self.get_settings(option, cast, False)
            w, h = self._get_frame_size()

            if self.rotate_angle != 0:
                if option == "counter_x":
                    if self.rotate_angle == 1:
                        if self.flip_v:
                            value = self.get_settings("counter_y", int, False)
                        else:
                            value = h - self.get_settings("counter_y", int, False) - \
                                    self.get_settings("counter_h", int, False)

                    elif self.rotate_angle == 2 and not self.flip_h:
                            value = w - self.get_settings("counter_x", int, False) - \
                                    self.get_settings("counter_w", int, False)

                    elif self.rotate_angle == 3:
                        if self.flip_v:
                            value = h - self.get_settings("counter_y", int, False) - \
                                    self.get_settings("counter_h", int, False)
                        else:
                            value = self.get_settings("counter_y", int, False)

                elif option == "counter_y":
                    if self.rotate_angle == 1:
                        if self.flip_h:
                            value = w - self.get_settings("counter_x", int, False) - \
                                    self.get_settings("counter_w", int, False)
                        else:
                            value = self.get_settings("counter_x", int, False)

                    elif self.rotate_angle == 2 and not self.flip_v:
                        value = h - self.get_settings("counter_y", int, False) - \
                                self.get_settings("counter_h", int, False)

                    elif self.rotate_angle == 3:
                        if self.flip_h:
                            value = self.get_settings("counter_x", int, False)
                        else:
                            value = w - self.get_settings("counter_x", int, False) - \
                                    self.get_settings("counter_w", int, False)

                elif option == "counter_w" and self.rotate_angle in [1, 3]:
                    value = self.get_settings("counter_h", int, False)

                elif option == "counter_h" and self.rotate_angle in [1, 3]:
                    value = self.get_settings("counter_w", int, False)

        logger.debug(f'{self._my_name}: {cast.__name__}({option}): {value} (in {(time.time() - _start_time)*1000:.2f} msec)')

        return value

    # ----------------------------------------------------------------------
    def save_settings(self, option, value):
        """
        saves the requested setting according the settings map

        :param option: str, setting name
        :param value: new vale to save
        :return:
        """

        logger.debug(f'{self._my_name}: setting {option}: new value {value}')

        if option in ["counter_x", "counter_y", "counter_w", "counter_h"]:

            w, h = self._get_frame_size()

            if self.rotate_angle != 0:
                if option == "counter_x":
                    if self.rotate_angle == 1:
                        option = "counter_y"
                        if not self.flip_v:
                            value = h - value - self.get_settings("counter_h", int, False)
                    elif self.rotate_angle == 2 and not self.flip_h:
                        value = w - value - self.get_settings("counter_w", int, False)
                    elif self.rotate_angle == 3:
                        if self.flip_v:
                            value = h - value - self.get_settings("counter_h", int, False)
                        option = "counter_y"

                elif option == "counter_y":
                    if self.rotate_angle == 1:
                        option = "counter_x"
                        if self.flip_h:
                            value = w - value - self.get_settings("counter_w", int, False)
                    elif self.rotate_angle == 2 and not self.flip_v:
                        value = h - value - self.get_settings("counter_h", int, False)
                    elif self.rotate_angle == 3:
                        option = "counter_x"
                        if not self.flip_h:
                            value = w - value - self.get_settings("counter_w", int, False)

                elif option == "counter_w" and self.rotate_angle in [1, 3]:
                    value = self.get_settings("counter_h", int, False)

                elif option == "counter_h" and self.rotate_angle in [1, 3]:
                    value = self.get_settings("counter_w", int, False)

        if option in self._settings_map.keys():
            if self._settings_map[option][0] == 'roi_server' and self._roi_server is not None:
                setattr(self._roi_server, self._settings_map[option][1], value)

            elif self._settings_map[option][0] == 'settings_proxy' and self._settings_proxy is not None:
                self._settings_proxy.write_attribute(self._settings_map[option][1], value)

            elif self._settings_map[option][0] == 'device_proxy' and self._device_proxy is not None:
                self._device_proxy.write_attribute(self._settings_map[option][1], value)

            elif self._settings_map[option][0] is None:
                pass

            else:
                raise RuntimeError(f'Unknown setting source {self._settings_map[option][0]}')
        else:
            QtCore.QSettings(APP_NAME).setValue("{}/{}".format(self._my_name, option), value)

        if option == 'Reduce':
            self.reduce_resolution = value

    # ----------------------------------------------------------------------
    # ------------------------ Screen control ------------------------------
    # ----------------------------------------------------------------------
    def has_motor(self):
        """

        :return: bool
        """
        return self._motor_worker is not None

    # ----------------------------------------------------------------------
    def move_motor(self, state=None):
        """

        :param state:
        :return:
        """
        if self._motor_worker is not None:
            if state is None:
                state = not self.motor_position()

            self._motor_worker.move_motor(state)

    # ----------------------------------------------------------------------
    def motor_position(self):
        """

        :return: bool: True - screen in, False - screen out, None is there is no motor
        """
        if self._motor_worker is not None:
            return self._motor_worker.motor_position()
        else:
            return None

    # ----------------------------------------------------------------------
    # ------------------------ Sardana counter control ---------------------
    # ----------------------------------------------------------------------
    def has_counter(self):
        """

        :return: bool
        """
        return getattr(self, self.counter_source) is not None

    # ----------------------------------------------------------------------
    def get_counter(self):
        """

        :return: str, current counter control
        """
        if getattr(self, self.counter_source) is not None:
            try:
                return getattr(getattr(self, self.counter_source), self.counter_name)
            except:
                return ''
        else:
            return ''

    # ----------------------------------------------------------------------
    def set_counter(self, value):
        """

        :param value: parameter to be set as a counter for Sardana control
        :return:
        """
        if getattr(self, self.counter_source) is not None:
            try:
                setattr(getattr(self, self.counter_source), self.counter_name, value)
            except:
                pass
