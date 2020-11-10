# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""General camera class
"""

import PyTango
import numpy as np

from PyQt5 import QtCore
from distutils.util import strtobool

from screen_motor import MotorExecutor

# ----------------------------------------------------------------------
class AbstractCamera(object):

    def __init__(self, beamline_id, settings, log):
        super(AbstractCamera, self).__init__()

        self._settings = settings
        self._log = log
        self._beamline_id = beamline_id

        self._cid = settings.getAttribute("name")

        self.flip_v = bool(strtobool(settings.getAttribute("flip_vertical")))
        self.flip_h = bool(strtobool(settings.getAttribute("flip_horizontal")))
        self.rotate_angle = int(settings.getAttribute("rotate"))


        self._device_proxy = PyTango.DeviceProxy(str(settings.getAttribute("tango_server")))
        if settings.hasAttribute('settings_server'):
            self._settings_proxy = PyTango.DeviceProxy(str(settings.getAttribute("settings_server")))
        else:
            self._settings_proxy = None

        if settings.hasAttribute('roi_server'):
            self._roi_server = PyTango.DeviceProxy(str(settings.getAttribute("roi_server")))
            no_need_to_init = True
            for prop in ['Flip_H', 'Flip_V']:
                pr = self._roi_server.get_property(prop)
                if strtobool(pr[prop][0]) != getattr(self, prop.lower()):
                    no_need_to_init *= False
                    pr[prop][0] = '{}'.format(getattr(self, prop.lower()))
                    self._roi_server.put_property(pr)

            pr = self._roi_server.get_property('Rotate_Angle')
            if int(pr['Rotate_Angle'][0]) != self.rotate_angle:
                no_need_to_init *= False
                pr[prop][0] = '{}'.format(self.rotate_angle)
                self._roi_server.put_property(pr)

            if not no_need_to_init:
                self._roi_server.init()
        else:
            self._roi_server = None

        if settings.hasAttribute('motor_type') and \
                (str(settings.getAttribute("motor_type")).lower() not in ['none', 'no', '']):
            self._motor_worker = MotorExecutor(settings, log)
        else:
            self._motor_worker = None
    # ----------------------------------------------------------------------
    def maybe_read_frame(self):
        """
        """
        if self._new_flag == False:
            return None

        self._new_flag = False
        return self.rotate()

    # ----------------------------------------------------------------------
    def rotate(self):

        if self.flip_v and self.flip_h:
            self._last_frame = self._last_frame[::-1, ::-1]
        elif self.flip_v:
            self._last_frame = self._last_frame[::, ::-1]
        elif self.flip_h:
            self._last_frame = self._last_frame[::-1, :]

        if self.rotate_angle:
            self._last_frame = np.rot90(self._last_frame, self.rotate_angle)

        return self._last_frame

    # ----------------------------------------------------------------------
    def get_settings(self, option, cast):

        if option in self._settings_map.keys():
            if self._settings_map[option][0] == 'roi_server' and self._roi_server is not None:
                return cast(getattr(self._roi_server, self._settings_map[option][1]))
            elif self._settings_map[option][0] == 'settings_proxy' and self._settings_proxy is not None:
                try:
                    value = self._settings_proxy.read_attribute(self._settings_map[option][1][0]).value
                except:
                    value = self._settings_proxy.read_attribute(self._settings_map[option][1][1]).value
                    self._settings_proxy.write_attribute(self._settings_map[option][1][0], value)
                return cast(value)
            elif self._settings_map[option][0] is None:
                return None
            else:
                raise RuntimeError('Unknown setting source')
        else:
            if cast == int:
                try:
                    value, _ = QtCore.QSettings("VimbaViewer", self._beamline_id).value(
                        "{}/{}".format(self._cid, option)).toInt()
                except:
                    value = 0
            elif cast == str:
                try:
                    value = QtCore.QSettings("VimbaViewer", self._beamline_id).value(
                        "{}/{}".format(self._cid, option)).toString()
                except:
                    value = ''
            elif cast == bool:
                try:
                    value = QtCore.QSettings("VimbaViewer", self._beamline_id).value(
                        "{}/{}".format(self._cid, option)).toBool()
                except:
                    value = False
            elif cast == float:
                try:
                    value, _ = QtCore.QSettings("VimbaViewer", self._beamline_id).value(
                        "{}/{}".format(self._cid, option)).toFloat()
                except:
                    value = 0.0
            else:
                try:
                    value = QtCore.QSettings("VimbaViewer", self._beamline_id).value(
                        "{}/{}".format(self._cid, option))
                except:
                    value = None

        return value

    # ----------------------------------------------------------------------
    def save_settings(self, setting, value):

        if setting in self._settings_map.keys():
            if self._settings_map[setting][0] == 'roi_server' and self._roi_server is not None:
                setattr(self._roi_server, self._settings_map[setting][1], value)
            elif self._settings_map[setting][0] == 'settings_proxy' and self._settings_proxy is not None:
                self._settings_proxy.write_attribute(self._settings_map[setting][1][0], value)
            elif self._settings_map[setting][0] is None:
                pass
            else:
                raise RuntimeError('Unknown setting source')
        else:
            QtCore.QSettings("VimbaViewer", self._beamline_id).setValue("{}/{}".format(self._cid, setting), value)

    # ----------------------------------------------------------------------
    def has_motor(self):
        return self._motor_worker is not None

    # ----------------------------------------------------------------------
    def move_motor(self, state=None):
        if self._motor_worker is not None:
            if state is None:
                state = not self.motor_position()

            self._motor_worker.move_motor(state)

    # ----------------------------------------------------------------------
    def motor_position(self):
        if self._motor_worker is not None:
            return self._motor_worker.motor_position()
        else:
            return None

    # ----------------------------------------------------------------------
    def has_counter(self):
        return self._roi_server is not None

    # ----------------------------------------------------------------------
    def get_counter(self):
        if self._roi_server is not None:
            return self._roi_server.scan_parameter
        else:
            return None

    # ----------------------------------------------------------------------
    def set_counter(self, value):
        if self._roi_server is not None:
             self._roi_server.scan_parameter = str(value)
