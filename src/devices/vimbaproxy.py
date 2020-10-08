#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de
# Last modified: 2017, December 13
# ----------------------------------------------------------------------

"""Vimba camera proxy
"""

import time

import numpy as np

try:
    import PyTango
except ImportError:
    pass


# ----------------------------------------------------------------------
class VimbaProxy(object):
    """Proxy to a physical TANGO device.
    """
    SERVER_SETTINGS = {'low': {"PixelFormat": "Mono8", "ViewingMode": 1},
                       'high': {"PixelFormat": "Mono12", "ViewingMode": 2},
                       'bhigh': {"PixelFormat": "BayerGR12", "ViewingMode": 2}}

    START_DELAY = 1
    STOP_DELAY = 0.5
    FPS = 2.

    # ----------------------------------------------------------------------
    def __init__(self, settings, generalSettings, log):
        super(VimbaProxy, self).__init__()

        self._tangoServer = settings.option("device", "tango_server")
        high_depth = settings.option("device", "high_depth")
        self._cid = settings.option("device", "name")

        self.log = log

        self._deviceProxy = PyTango.DeviceProxy(str(self._tangoServer))
        self.log.info("Ping {} ({})".format(self._tangoServer,
                                            self._deviceProxy.ping()))
        if high_depth == "True":
            valid_formats = self._deviceProxy.read_attribute('PixelFormat#Values').value
            if "Mono12" in valid_formats:
                settings = 'high'
                depth = 16
            elif 'BayerGR12' in valid_formats:
                settings = 'bhigh'
                depth = 16
        else:
            settings = 'low'
            depth = 8
        self._newFlag = False
        self.errorMsg = ''
        self.errorFlag = False
        self._lastFrame = np.zeros((1, 1))

        if self._deviceProxy.state() == PyTango.DevState.RUNNING:
            self._deviceProxy.StopAcquisition()
        for k, v in self.SERVER_SETTINGS[settings].items():
            print(k,v)
            self._deviceProxy.write_attribute(k, v)

        self._eid = self._deviceProxy.subscribe_event("Image{:d}".format(depth),
                                                      PyTango.EventType.DATA_READY_EVENT,
                                                      self._readoutFrame, [], True)

    # ----------------------------------------------------------------------
    def maybeReadFrame(self):
        """
        """
        if self._newFlag == False:
            return None

        self._newFlag = False
        return self._lastFrame

    # ----------------------------------------------------------------------
    def startAcquisition(self):
        """
        """
        self.log.info("Start camera...")

        if self._deviceProxy.state() == PyTango.DevState.ON:
            self._deviceProxy.write_attribute('TriggerSource','FixedRate')
            self._deviceProxy.command_inout("StartAcquisition")
            time.sleep(self.START_DELAY)  # ? TODO
        else:
            self.log.warning("Camera should be in ON state (is it running already?)")

    # ----------------------------------------------------------------------
    def stopAcquisition(self):
        """
        """
        self.log.info("Stop camera...")

        if self._deviceProxy.state() == PyTango.DevState.RUNNING:
            self._deviceProxy.unsubscribe_event(self._eid)
            self._deviceProxy.command_inout("StopAcquisition")

            time.sleep(self.STOP_DELAY)  # ? TODO

    # ----------------------------------------------------------------------
    def _readoutFrame(self, event):
        """Called each time new frame is available.
        """
        if not self._deviceProxy:
            self.log.error("VimbaTango DeviceProxy error")

        # we do this on every frame since we had problems in the past with this value getting reset
        # it's possible that this has to do with TriggerSource not being set to FixedRate in some cases before
        exp = event.device.read_attribute("ExposureTimeAbs").value * 1e-6
        max_fps = event.device.read_attribute("AcquisitionFrameRateLimit").value
        if 1. / exp < self.FPS or self.FPS > max_fps:
            event.device.write_attribute("AcquisitionFrameRateAbs", max_fps)
            # print("FPS determined by external factor")
        else:
            event.device.write_attribute("AcquisitionFrameRateAbs", self.FPS)
            # print("FPS determined by internal factor")

        # for some reason this wants the 'short' attribute name, not the fully-qualified name
        # we get in event.attr_name
        if not event.err:
            try:
                data = event.device.read_attribute(event.attr_name.split('/')[6])
                self._lastFrame = np.transpose(data.value)
                # self._lastFrame = np.copy(data.value)

                # lock = QtCore.QMutexLocker(self._flagMutex)             # ? TODO
                self._newFlag = True
            except Exception as err:
                print ('Got an error: {}'.format(err))
                self.errorFlag = True
                self.errorMsg = str(err)
        else:
            print ('Got an error: {}'.format(self.errorMsg))
            self.errorFlag = True
            self.errorMsg = event.errors
