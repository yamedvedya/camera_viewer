#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        patrick.loemker@desy.de
# Last modified: 2018, July 10
# ----------------------------------------------------------------------

"""TangotoTine camera proxy
"""

import numpy as np

try:
    import PyTango
except ImportError:
    pass


# ----------------------------------------------------------------------
class TangoTineProxy(object):
    """Proxy to a physical TANGO device.
    """
    # SERVER_SETTINGS = {"PixelFormat": "Mono8",  # possibly more...
    #                    "ViewingMode": 1}

    START_DELAY = 1
    STOP_DELAY = 0.5

    # ----------------------------------------------------------------------
    def __init__(self, settings, generalSettings, log):
        super(TangoTineProxy, self).__init__()

        self._tangoServer = settings.option("device", "tango_server")
        self._settingsServer = settings.option("device", "settings_server")
        self._cid = settings.option("device", "name")

        self.log = log

        self._deviceProxy = PyTango.DeviceProxy(str(self._tangoServer))
        self._settingsProxy = PyTango.DeviceProxy(str(self._settingsServer))
        self.log.info("Ping {} ({})".format(self._tangoServer,
                                            self._deviceProxy.ping()))
        self.log.info("Ping {} ({})".format(self._settingsServer,
                                            self._settingsProxy.ping()))
        #
        # for k, v in self.SERVER_SETTINGS.items():
        #     self._deviceProxy.write_attribute(k, v)

        self._newFlag = False
        self.errorFlag = False
        self.errorMsg = ''
        self._lastFrame = np.zeros((1, 1))
        self.period = 200
        if not self._deviceProxy.is_attribute_polled('Frame'):
            self._deviceProxy.poll_attribute('Frame', self.period)
        self.self_period = not self._deviceProxy.get_attribute_poll_period("Frame") == self.period
        if self.self_period:
            self._deviceProxy.stop_poll_attribute("Frame")
            self._deviceProxy.poll_attribute('Frame', self.period)
        self._eid = self._deviceProxy.subscribe_event("Frame", PyTango.EventType.PERIODIC_EVENT, self._readoutFrame)

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
        pass

    # ----------------------------------------------------------------------
    def stopAcquisition(self):
        pass

    # ----------------------------------------------------------------------
    def _readoutFrame(self, event):
        """Called each time new frame is available.
        """
        if not self._deviceProxy:
            self.log.error("TangoTineTango DeviceProxy error")

        # for some reason this wants the 'short' attribute name, not the fully-qualified name
        # we get in event.attr_name
        data = event.device.read_attribute(event.attr_name.split('/')[6])
        self._lastFrame = np.transpose(data.value)
        self._newFlag = True
