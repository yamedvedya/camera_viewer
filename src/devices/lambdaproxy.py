# Created by matveyev at 01.12.2020

# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------


"""Dalsa camera proxy
"""

import numpy as np
import PyTango
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import os.path as ospath

from PIL import Image

from src.devices.abstract_camera import AbstractCamera

# ----------------------------------------------------------------------
class LambdaProxy(AbstractCamera):

    _settings_map = {
                     'max_level_limit': (None, ),
                     'max_width': ('self', 'MAX_W'),
                     'max_height': ('self', 'MAX_H')}

    visible_layouts = ('folder', 'source')

    MAX_W = 1556
    MAX_H = 516

    # ----------------------------------------------------------------------
    def __init__(self, beamline_id, settings, log):
        super(LambdaProxy, self).__init__(beamline_id, settings, log)

        if settings.hasAttribute('folders'):
            self._possible_folders = [item.strip() for item in settings.getAttribute("folders").split(';')]
        else:
            self._possible_folders = ['/gpfs/current/raw/', '/gpfs/commissioning/raw/']

        if settings.hasAttribute('sources'):
            self._possible_sources = [item.strip() for item in settings.getAttribute("folders").split(';')]
        else:
            self._possible_sources = ['Event', 'Files']

        self._my_event_handler = PatternMatchingEventHandler(["*.nxs"], "", False, True)
        self._my_event_handler.on_created = self._on_created

        self._my_observer = None

        self._source = self._possible_sources[0]

        self.path = self._possible_folders[0]

        self._last_frame = np.zeros((1, 1))

        self.error_flag = False
        self.error_msg = ''

        self._running = False

    # ----------------------------------------------------------------------
    def start_acquisition(self):

        if self._source == 'Event':
            if self._device_proxy is None:
                raise RuntimeError('No device proxy')

            self._eid = self._device_proxy.subscribe_event("LiveLastImageData",
                                                           PyTango.EventType.DATA_READY_EVENT, self._on_event)
            self._running = True
            return True

        elif self._source == 'Files':
            if self.path != '':
                self._my_observer = Observer()
                self._my_observer.schedule(self._my_event_handler, self.path, recursive=True)
                self._my_observer.start()
                self._running = True
                return True
            else:
                raise RuntimeError('Path is not exist')
        else:
            raise RuntimeError('Unknown mode')

    # ----------------------------------------------------------------------
    def stop_acquisition(self):

        if self._source == 'Event':
            self._device_proxy.unsubscribe_event(self._eid)
        elif self._source == 'Files':
            self._my_observer.stop()
            self._my_observer.join()
        else:
            raise RuntimeError('Unknown mode')
        self._running = False

        self._log.debug("Dalsa folder monitor unsubscribed")

    # ----------------------------------------------------------------------
    def _on_event(self, event):
        if not event.err:
            data = event.device.read_attribute(event.attr_name.split('/')[6])
            self._last_frame = np.array(data.value)[self._picture_size[0]:self._picture_size[2],
                                                    self._picture_size[1]:self._picture_size[3]]

            self._new_frame_flag = True
        else:
            print('Event error!')
            # self._log.error('Tine error: {}'.format(self.error_msg))
            # self.error_flag = True
            # self.error_msg = event.errors
    # ----------------------------------------------------------------------
    def _on_created(self, event):

        self.id = ' file: {}'.format(ospath.splitext(ospath.basename(event.src_path))[0])
        self._last_frame = np.array(Image.open(event.src_path))[self._picture_size[0]:self._picture_size[2],
                                                                self._picture_size[1]:self._picture_size[3]]
        self._new_frame_flag = True

    # ----------------------------------------------------------------------
    def _set_new_path(self, path):
        need_to_restart = self._running
        if self._running:
            self.stop_acquisition()
            self._last_frame = np.zeros((1, 1))
            self._new_frame_flag = True

        self.path = path

        if need_to_restart:
            self.start_acquisition()

    # ----------------------------------------------------------------------
    def get_settings(self, option, cast):

        if option == 'Path':
            path = super(LambdaProxy, self).get_settings(option, cast)
            if path != '':
                self._set_new_path(path)
            return self.path

        elif option == 'Source':
            source = super(LambdaProxy, self).get_settings(option, cast)
            if source != '':
                self._change_source(source)
            return self._source

        if option == 'max_width':
            return 1556

        elif option == 'max_height':
            return 516

        elif option == 'possible_sources':

            return self._possible_sources

        elif option == 'possible_folders':
            return self._possible_folders

        else:
            return super(LambdaProxy, self).get_settings(option, cast)

    # ----------------------------------------------------------------------
    def save_settings(self, setting, value):
        if setting == 'Path':
            self._set_new_path(value)

        elif setting == 'Source':
            self._change_source(value)

        super(LambdaProxy, self).save_settings(setting, value)

    # ----------------------------------------------------------------------
    def _change_source(self, source):
        need_to_restart = self._running
        if self._running:
            self.stop_acquisition()
            self._last_frame = np.zeros((1, 1))
            self._new_frame_flag = True

        self._source = source

        if need_to_restart:
            self.start_acquisition()