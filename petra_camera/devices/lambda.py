# Created by matveyev at 01.12.2020

# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------


"""Dalsa camera proxy
"""

import numpy as np
import tango
import logging
import os.path as ospath

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from PIL import Image

from petra_camera.devices.base_camera import BaseCamera

from petra_camera.constants import APP_NAME
logger = logging.getLogger(APP_NAME)


# ----------------------------------------------------------------------
class LambdaProxy(BaseCamera):

    _settings_map = {'max_width': ('self', 'MAX_W'),
                     'max_height': ('self', 'MAX_H')}

    visible_layouts = ('folder', 'source')

    MAX_W = 1556
    MAX_H = 516

    # ----------------------------------------------------------------------
    def __init__(self, settings):
        super(LambdaProxy, self).__init__(settings)

        if 'folders' in settings.keys():
            self._possible_folders = [item.strip() for item in settings.get("folders").split(';')]
        else:
            self._possible_folders = ['/gpfs/current/raw/', '/gpfs/commissioning/raw/']

        if 'sources' in settings.keys():
            self._possible_sources = [item.strip() for item in settings.get("folders").split(';')]
        else:
            self._possible_sources = ['Event', 'Files']

        self._my_event_handler = PatternMatchingEventHandler(["*.nxs"], "", False, True)
        self._my_event_handler.on_created = self._on_created

        self._my_observer = None

        self._source = self._possible_sources[0]

        self.path = self._possible_folders[0]

        self._last_frame = np.zeros((1, 1))

        self._running = False

    # ----------------------------------------------------------------------
    def _start_acquisition(self):

        if self._source == 'Event':
            if self._device_proxy is not None:
                logger.debug(f'{self._my_name}: starting acquisition: event mode')

                self._eid = self._device_proxy.subscribe_event("LiveLastImageData",
                                                               tango.EventType.DATA_READY_EVENT, self._on_event)
                self._running = True

        elif self._source == 'Files':

            if self.path != '':
                logger.debug(f'{self._my_name}: starting acquisition: files mode')

                self._my_observer = Observer()
                self._my_observer.schedule(self._my_event_handler, self.path, recursive=True)
                self._my_observer.start()
                self._running = True

        return self._running

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

        logger.debug(f"{self._my_name} stopping acquisition: unsubscribed")

    # ----------------------------------------------------------------------
    def _on_event(self, event):
        self.error_flag = False
        self.error_msg = ""
        if not event.err:
            try:
                data = event.attr_value
                if data.quality == tango.AttrQuality.ATTR_VALID:
                    self._last_frame = self._process_frame(data.value)
                    self._new_frame_flag = True
                    return
                else:
                    err = f"{self._my_name} error: AttrQuality is {data.quality}"
            except Exception as err:
                pass
        else:
            err = event.errors
        self.error_flag = True
        self.error_msg = str(err)
        logger.error(f'{self._my_name} error: {err}', exc_info=True)
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
    def get_settings(self, option, cast, do_rotate=True, do_log=True):

        if option in ['Path', 'Source', 'max_width', 'max_height']:

            logger.debug(f'{self._my_name}: setting {cast.__name__}({option}) requested')

            if option == 'Path':
                path = super(LambdaProxy, self).get_settings(option, cast, do_rotate, do_log)
                if path != '':
                    self._set_new_path(path)
                return self.path

            elif option == 'Source':
                source = super(LambdaProxy, self).get_settings(option, cast, do_rotate, do_log)
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
            return super(LambdaProxy, self).get_settings(option, cast, do_rotate, do_log)

    # ----------------------------------------------------------------------
    def save_settings(self, option, value):

        if option in ['Path', 'Source']:
            logger.debug(f'{self._my_name}: setting {option}: new value {value}')

            if option == 'Path':
                self._set_new_path(value)

            elif option == 'Source':
                self._change_source(value)

        super(LambdaProxy, self).save_settings(option, value)

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