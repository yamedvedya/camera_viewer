# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""

import importlib
import logging
import threading
import time
import json

import numpy as np
from src.utils.errors import report_error

from PyQt5 import QtCore


# ----------------------------------------------------------------------
class DataSource2D(QtCore.QObject):
    """
    """
    newFrame = QtCore.pyqtSignal()
    gotError = QtCore.pyqtSignal(str)

    # ----------------------------------------------------------------------
    def __init__(self, parent):
        """
        """
        super(DataSource2D, self).__init__(parent)

        self._parent = parent
        self.settings = parent.settings

        self.log = logging.getLogger("cam_logger")  # is in sync with the main thread? TODO

        self.device_id = ''
        self._base_id = ''

        self.image_need_repaint = False
        self.image_need_refresh = False

        self.rois = []
        self.rois_data = []
        self.roi_need_update = False
        self.roi_changed = False
        self._counter_roi = 0

        self.markers = []
        self.markers_need_update = False
        self.markers_changed = False

        self.peak_search = {}
        self.peak_search_need_update = False

        self.levels = []
        self.level_mode = 'lin'

        self.auto_screen = False

        self._dark_image = None
        self.subtract_dark_image = False

        self._device_proxy = None
        self._worker = None

        self._frame_mutex = QtCore.QMutex()  # sync access to frame
        self._last_frame = np.zeros((1, 1))

        self.got_first_frame = False

        self._state = "idle"
        self.fps = 1

    # ----------------------------------------------------------------------
    def _reset_worker(self):
        """
        """
        if self._worker:
            self._state = 'abort'
            self._worker.join()

        self._worker = threading.Thread(target=self.run)

    # ----------------------------------------------------------------------
    def start(self, auto_screen):
        """
        """
        self._reset_worker()
        self._worker.start()

        if self.auto_screen and auto_screen:
            self._device_proxy.move_motor(True)

    # ----------------------------------------------------------------------
    def stop(self, auto_screen):
        """
        """
        if self._state != 'idle':
            self._state = "abort"

        while self._state != 'idle':
            time.sleep(1e-3)

        if self.auto_screen and auto_screen:
            self._device_proxy.move_motor(False)

        self.log.debug('CameraDevice stopped')

    # ----------------------------------------------------------------------
    def set_new_level_mode(self, mode):

        if self.level_mode != mode:
            self.level_mode = mode
            self.save_settings('level_mode', mode)
            if self.got_first_frame:
                self.newFrame.emit()

    # ----------------------------------------------------------------------
    def run(self):
        """
        """
        if self._start_acquisition():

            while self._state == "running":

                frame = self._device_proxy.maybe_read_frame()
                if frame is not None:
                    self.got_first_frame = True
                    self._last_frame = frame
                    self.newFrame.emit()
                    self.device_id = self._base_id + self._device_proxy.id

                if self._device_proxy.error_flag:
                    self.gotError.emit(str(self._device_proxy.error_msg))
                    self._state = "abort"

                time.sleep(1/self.fps)
            self.log.info("Closing {}...".format(self.device_id))

            if self._device_proxy:
                self._device_proxy.stop_acquisition()

        self._state = "idle"

    # ----------------------------------------------------------------------
    def _start_acquisition(self):
        """
        """
        if self._device_proxy:

            try:
                if self._device_proxy.start_acquisition():
                    self._state = "running"
                    return True
                else:
                    return False

            except Exception as err:
                report_error(err, self.log, self._parent)
                return False

    # ----------------------------------------------------------------------
    def get_settings(self, setting, cast):

        if self._device_proxy:
            if setting == 'FPS':
                self.fps = max(1, self._device_proxy.get_settings('FPS', int))
                return self.fps
            else:
                return self._device_proxy.get_settings(setting, cast)
        else:
            return None

    # ----------------------------------------------------------------------
    def save_settings(self, setting, value):
        if self._device_proxy:
            if setting == 'FPS':
                self.fps = value

            self._device_proxy.save_settings(setting, value)

    # ----------------------------------------------------------------------
    def get_frame(self):
        """
        """
        if self.subtract_dark_image and self._dark_image is not None:
            try:
                invalid_idx = self._last_frame < self._dark_image
                frame = self._last_frame - self._dark_image
                frame[invalid_idx] = 0
            except:
                self.subtract_dark_image = False
                self._dark_image = None
                frame = self._last_frame
        else:
            frame = self._last_frame

        if self.level_mode == 'sqrt':
            frame = np.sqrt(np.abs(frame))
        elif self.level_mode == 'log':
            frame = np.log(np.maximum(1, frame))

        if np.max(frame) == 0:
            return np.ones_like(frame)
        else:
            return frame

    # ----------------------------------------------------------------------
    def set_dark_image(self):
        self._dark_image = self._last_frame

    # ----------------------------------------------------------------------
    def load_dark_image(self, file_name):
        self._dark_image = np.load(file_name)

    # ----------------------------------------------------------------------
    def save_dark_image(self, file_name):
        np.save(file_name, self._dark_image)

    # ----------------------------------------------------------------------
    def has_dark_image(self):
        return self._dark_image is not None

    # ----------------------------------------------------------------------
    def toggle_dark_image(self, state):
        if self._dark_image is not None:
            self.subtract_dark_image = state

        if self.got_first_frame:
            self.newFrame.emit()

    # ----------------------------------------------------------------------
    def close_camera(self):

        if self._device_proxy is not None:
            self._device_proxy.close_camera()

    # ----------------------------------------------------------------------
    def new_device_proxy(self, name, auto_screen):

        for device in self.settings.get_nodes('camera_viewer', 'camera'):
            if device.getAttribute('name') == name:

                self.device_id = name
                self._base_id = name

                try:
                    proxyClass = device.getAttribute("proxy")
                    self.log.info("Loading device proxy {}...".format(proxyClass))

                    module = importlib.import_module("devices.{}".format(proxyClass.lower()))
                    self._device_proxy = getattr(module, proxyClass)(device, self.log)
                    self.got_first_frame = False
                    self._last_frame = np.zeros((1, 1))

                    lut = self.get_settings('lut', str)
                    if lut != '':
                        self.levels = json.loads(lut)
                    else:
                        self.levels = {'gradient': {'mode': 'rgb',
                                                    'ticks': [(0.0, (0, 0, 0, 255)), (1.0, (255, 255, 255, 255))],
                                                    'ticksVisible': True},
                                       'levels': (0, 255.0),
                                       'mode': 'mono',
                                       'auto_levels': True}

                    self.level_mode = self.get_settings('level_mode', str)
                    if self.level_mode == '':
                        self.level_mode = 'lin'

                    self.image_need_repaint = True

                    self.auto_screen = self.get_settings('auto_screen', bool)

                    self.rois = []
                    self.rois_data = []
                    self._counter_roi = self.get_settings('counter_roi', int)
                    self._counter_param = self.get_settings('counter_roi', int)

                    for ind in range(self.get_settings('num_rois', int)):
                        self.rois.append({'x': self.get_settings('roi_{}_x'.format(ind), int),
                                          'y': self.get_settings('roi_{}_y'.format(ind), int),
                                          'w': self.get_settings('roi_{}_w'.format(ind), int),
                                          'h': self.get_settings('roi_{}_h'.format(ind), int),
                                          'bg': self.get_settings('roi_{}_bg'.format(ind), int),
                                          'visible': self.get_settings('roi_{}_visible'.format(ind), bool),
                                          'mark': self.get_settings('roi_{}_mark'.format(ind), str),
                                          'color': self.get_settings('roi_{}_color'.format(ind), str)})

                        if ind == self._counter_roi:
                            for setting in ['x', 'y', 'w', 'h']:
                                self.save_settings('counter_{}'.format(setting), self.rois[ind][setting])

                        self.rois_data.append(dict.fromkeys(['max_x', 'max_y', 'max_v',
                                                             'min_x', 'min_y', 'min_v',
                                                             'com_x', 'com_y', 'com_v',
                                                             'fwhm_x', 'fwhm_y', 'sum']))

                    self.roi_changed = True
                    self.roi_need_update = True

                    self.markers = []
                    for ind in range(self.get_settings('num_markers', int)):
                        self.markers.append({'x': self.get_settings('marker_{}_x'.format(ind), int),
                                             'y': self.get_settings('marker_{}_y'.format(ind), int),
                                             'visible': self.get_settings('marker_{}_visible'.format(ind), bool),
                                             'color': self.get_settings('marker_{}_color'.format(ind), str)})

                    self.markers_changed = True
                    self.markers_need_update = True

                    self.peak_search = {'search': False, #TODO: need solution for wrong settings!
                                        'search_mode': self.get_settings('peak_search_mode', bool),
                                        'rel_threshold': self.get_settings('peak_rel_threshold', int),
                                        'abs_threshold': self.get_settings('peak_abs_threshold', int)}

                    if self.peak_search['rel_threshold'] == 0:
                        self.peak_search['rel_threshold'] = 80

                    if self.peak_search['abs_threshold'] == 0:
                        self.peak_search['abs_threshold'] = 16000

                    self.peak_search_need_update = True

                    if self._device_proxy.is_running():
                        self.start(auto_screen)

                    return True

                except Exception as ex:
                    self.log.error(ex)
                    return False

        return False

    # ----------------------------------------------------------------------
    def set_peak_search_value(self, setting, value):
        self.peak_search_need_update = True
        self.peak_search[setting] = value
        self.save_settings('peak_{}'.format(setting), value)

    # ----------------------------------------------------------------------
    def _save_marker_settings(self):
        num_markers = len(self.markers)
        self.save_settings('num_markers', num_markers)
        for ind, marker in enumerate(self.markers):
            for param in ['x', 'y', 'visible', 'color']:
                self.save_settings('marker_{}_{}'.format(ind, param), marker[param])

    # ----------------------------------------------------------------------
    def set_marker_value(self, marker_id, setting, value):
        self.markers_need_update = True
        self.markers[marker_id][setting] = value
        self.save_settings('marker_{}_{}'.format(marker_id, setting), value)

    # ----------------------------------------------------------------------
    def append_marker(self):
        self.markers_changed = True
        self.markers.append({'x': 0, 'y': 0, 'visible': True, 'color': self.settings.option('colors', 'marker')})
        self._save_marker_settings()

    # ----------------------------------------------------------------------
    def delete_marker(self, index):
        self.markers_changed = True
        del self.markers[index]
        self._save_marker_settings()

    # ----------------------------------------------------------------------
    def _save_roi_settings(self):
        num_rois = len(self.rois)
        self.save_settings('num_rois', num_rois)
        for ind, roi in enumerate(self.rois):
            for param in ['x', 'y', 'w', 'h', 'bg', 'visible', 'mark']:
                self.save_settings('roi_{}_{}'.format(ind, param), roi[param])

    # ----------------------------------------------------------------------
    def set_roi_value(self, roi_id, setting, value):
        self.roi_need_update = True
        self.rois[roi_id][setting] = value
        self.save_settings('roi_{}_{}'.format(roi_id, setting), value)

        if roi_id == self._counter_roi:
            if setting in ['x', 'y', 'w', 'h']:
                self.save_settings('counter_{}'.format(setting), value)

    # ----------------------------------------------------------------------
    def num_roi(self):
        return len(self.rois)

    # ----------------------------------------------------------------------
    def get_counter_roi(self):
        return self._counter_roi

    # ----------------------------------------------------------------------
    def set_counter_roi(self, value):
        self._counter_roi = value
        self.save_settings('counter_roi', value)
        for setting in ['x', 'y', 'w', 'h']:
            if len(self.rois):
                self.save_settings('counter_{}'.format(setting), self.rois[value][setting])

    # ----------------------------------------------------------------------
    def get_active_roi_value(self, value):
        return self.rois_data[self._counter_roi][value]

    # ----------------------------------------------------------------------
    def add_roi(self):
        self.roi_changed = True
        self.rois.append({'x': 0, 'y': 0, 'w': 50, 'h': 50, 'bg': 0, 'visible': True, 'mark': '',
                          'color': self.settings.option('colors', 'roi')})
        self.rois_data.append(dict.fromkeys(['max_x', 'max_y', 'max_v',
                                             'min_x', 'min_y', 'min_v',
                                             'com_x', 'com_y', 'com_v',
                                             'fwhm_x', 'fwhm_y', 'sum']))

        self._save_roi_settings()

    # ----------------------------------------------------------------------
    def delete_roi(self, index):
        self.roi_changed = True
        del self.rois[index]
        del self.rois_data[index]
        self._save_roi_settings()

    # ----------------------------------------------------------------------
    def level_setting_change(self, lut_state):
        self.image_need_repaint = True
        self.levels = lut_state
        self.save_settings('lut', json.dumps(lut_state))

    # ----------------------------------------------------------------------
    def is_running(self):
        if self._device_proxy is None:
            return None
        else:
            return self._device_proxy.is_running()

    # ----------------------------------------------------------------------
    def has_motor(self):
        return self._device_proxy.has_motor()

    # ----------------------------------------------------------------------
    def move_motor(self, new_state=None):

        self._device_proxy.move_motor(new_state)

    # ----------------------------------------------------------------------
    def motor_position(self):

        if self._device_proxy is not None:
            return self._device_proxy.motor_position()

        return None

    # ----------------------------------------------------------------------
    def has_counter(self):
        if self._device_proxy is not None:
            return self._device_proxy.has_counter()

        return False

    # ----------------------------------------------------------------------
    def get_counter(self):
        if self._device_proxy is not None:
            return self._device_proxy.get_counter()

        return ""

    # ----------------------------------------------------------------------
    def set_counter(self, value):
        self._device_proxy.set_counter(value)

    # ----------------------------------------------------------------------
    def visible_layouts(self):
        return self._device_proxy.visible_layouts

    # ----------------------------------------------------------------------
    def set_picture_clip(self, size):
        self.image_need_refresh = True
        self.save_settings('view_x', size[0])
        self.save_settings('view_y', size[1])
        self.save_settings('view_w', size[2])
        self.save_settings('view_h', size[3])
        self._device_proxy.set_picture_clip(size)

    # ----------------------------------------------------------------------
    def get_picture_clip(self):
        return self._device_proxy.get_picture_clip()

    # ----------------------------------------------------------------------
    def get_max_picture_size(self):
        return self._device_proxy.get_settings('max_width', int), self._device_proxy.get_settings('max_height', int)

    # ----------------------------------------------------------------------
    def get_device_source(self):
        return self._device_proxy.source_mode

    # ----------------------------------------------------------------------
    def get_reduction(self):
        return self._device_proxy.get_reduction()

    # ----------------------------------------------------------------------
    def set_reduction(self, value):
        self._device_proxy.set_reduction(value)

    # ----------------------------------------------------------------------
    def set_auto_screen(self, state):
        self.auto_screen = state
        self.save_settings('auto_screen', state)