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

from abstract_camera import AbstractCamera

try:
    import PyTango
except ImportError:
    pass


# ----------------------------------------------------------------------
class VimbaProxy(AbstractCamera):
    """Proxy to a physical TANGO device.
    """
    SERVER_SETTINGS = {'low': {"PixelFormat": "Mono8", "ViewingMode": 1},
                       'high': {"PixelFormat": "Mono12", "ViewingMode": 2},
                       'bhigh': {"PixelFormat": "BayerGR12", "ViewingMode": 2}}

    START_DELAY = 1
    STOP_DELAY = 0.5
    FPS = 2.

    # ----------------------------------------------------------------------
    def __init__(self, beamline_id, settings, log):
        super(VimbaProxy, self).__init__(beamline_id, settings, log)

        self._tangoServer = settings.option("device", "tango_server")
        high_depth = settings.option("device", "high_depth")
        self._cid = settings.option("device", "name")

        self._exposureName = "ExposureTimeAbs"
        self._viewX_name = "OffsetX"
        self._viewY_name = "OffsetY"
        self._viewH_name = "Height"
        self._viewHmax_name = "HeightMax"
        self._viewW_name = "Width"
        self._viewWmax_name = "WidthMax"
        self.hMax = self._device_proxy.read_attribute(self._viewHmax_name).value
        self.wMax = self._device_proxy.read_attribute(self._viewWmax_name).value
        self._gainName = str(self._device_proxy.get_property('GainFeatureName')['GainFeatureName'][0])
        self._high_depth = settings.option("device", "high_depth")

        if self._high_depth:
            self._ui.sbMaxLevel.setMaximum(2 ** 12)
            self._ui.sbMinLevel.setMaximum(2 ** 12)
        else:
            self._ui.sbMaxLevel.setMaximum(2 ** 8)
            self._ui.sbMinLevel.setMaximum(2 ** 8)


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


    def get_settings(self, option, cast):


        self._tangoServer = settings.option("device", "tango_server")
        self._deviceProxy = PyTango.DeviceProxy(str(self._tangoServer))
        self._exposureName = "ExposureTimeAbs"
        self._viewX_name = "OffsetX"
        self._viewY_name = "OffsetY"
        self._viewH_name = "Height"
        self._viewHmax_name = "HeightMax"
        self._viewW_name = "Width"
        self._viewWmax_name = "WidthMax"
        self.hMax = self._deviceProxy.read_attribute(self._viewHmax_name).value
        self.wMax = self._deviceProxy.read_attribute(self._viewWmax_name).value
        # self._deviceProxy.write_attribute(self._viewX_name, 0)
        # self._deviceProxy.write_attribute(self._viewY_name, 0)
        # self._deviceProxy.write_attribute(self._viewW_name, self.wMax)
        # self._deviceProxy.write_attribute(self._viewH_name, self.hMax)

        self._gainName = str(self._deviceProxy.get_property('GainFeatureName')['GainFeatureName'][0])
        self._high_depth = settings.option("device", "high_depth")

        if self._high_depth:
            self._ui.sbMaxLevel.setMaximum(2 ** 12)
            self._ui.sbMinLevel.setMaximum(2 ** 12)
        else:
            self._ui.sbMaxLevel.setMaximum(2 ** 8)
            self._ui.sbMinLevel.setMaximum(2 ** 8)

        fps = self._deviceProxy.read_attribute("AcquisitionFrameRateAbs").value

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

                self._newFlag = True
            except Exception as err:
                print ('Got an error: {}'.format(err))
                self.errorFlag = True
                self.errorMsg = str(err)
        else:
            print ('Got an error: {}'.format(self.errorMsg))
            self.errorFlag = True
            self.errorMsg = event.errors
