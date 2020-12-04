# Created by matveyev at 01.12.2020

# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------


"""Dalsa camera proxy
"""

import numpy as np
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import os.path as ospath

from PIL import Image

from src.devices.abstract_camera import AbstractCamera

# ----------------------------------------------------------------------
class DalsaProxy(AbstractCamera):

    _settings_map = {
                     'max_level_limit': (None, )
                     }

    visible_layouts = ('Folder',)

    # ----------------------------------------------------------------------
    def __init__(self, beamline_id, settings, log):
        super(DalsaProxy, self).__init__(beamline_id, settings, log)

        if settings.hasAttribute('folders'):
            self._possible_folders = [item.strip() for item in settings.getAttribute("folders").split(';')]
        else:
            self._possible_folders = ['/gpfs/current/raw/', '/gpfs/commissioning/raw/']

        self._my_event_handler = PatternMatchingEventHandler(["*.tif"], "", False, True)
        self._my_event_handler.on_created = self.on_created

        self._my_observer = None

        self.path = self._possible_folders[0]

        self._picture_size = [0, 0, -1, -1]
        self._last_frame = np.zeros((1, 1))

        self.error_flag = False
        self.error_msg = ''

        self._running = False

    # ----------------------------------------------------------------------
    def start_acquisition(self):

        if self.path != '':
            self._my_observer = Observer()
            self._my_observer.schedule(self._my_event_handler, self.path, recursive=True)
            self._my_observer.start()
            self._running = True
        else:
            raise RuntimeError('Path is empty')

    # ----------------------------------------------------------------------
    def stop_acquisition(self):

        self._my_observer.stop()
        self._my_observer.join()
        self._running = False

        self._log.debug("Dalsa folder monitor unsubscribed")

    # ----------------------------------------------------------------------
    def on_created(self, event):

        self.id = ' file: {}'.format(ospath.splitext(ospath.basename(event.src_path))[0])
        self._last_frame = np.array(Image.open(event.src_path))[self._picture_size[0]:self._picture_size[2],
                                                        self._picture_size[1]:self._picture_size[3]]
        self._new_frame_flag = True

    # ----------------------------------------------------------------------
    def _set_new_path(self, path):
        if self._running:
            self.stop_acquisition()
            self._last_frame = np.zeros((1, 1))
            self._new_frame_flag = True

        self.path = path

        if self._running:
            self.start_acquisition()

    # ----------------------------------------------------------------------
    def get_settings(self, option, cast):

        if option == 'Path':
            path = super(DalsaProxy, self).get_settings(option, cast)
            if path != '':
                self._set_new_path(path)
            return self.path

        elif option == 'possible_folders':
            return self._possible_folders

        else:
            return super(DalsaProxy, self).get_settings(option, cast)

    # ----------------------------------------------------------------------
    def save_settings(self, setting, value):
        if setting == 'Path':
            self._set_new_path(value)

        super(DalsaProxy, self).save_settings(setting, value)

    # ----------------------------------------------------------------------
    def change_picture_size(self, size):

        # self._picture_size = [size[0], size[1], size[0]+size[2], size[1]+size[3]]
        pass