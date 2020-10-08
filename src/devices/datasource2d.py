#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de
# Last modified: 2017, December 6
# ----------------------------------------------------------------------

"""Thin wrapper around TANGO Vimba server.
(can be treated as a "data source" in ectrl...?)
"""

import importlib
import logging
import threading
import time

import numpy as np

from PyQt4 import QtCore


# ----------------------------------------------------------------------
class DataSource2D(QtCore.QObject):
    """
    """
    newFrame = QtCore.Signal()
    gotError = QtCore.Signal(str)

    TICK = 0.1

    # ----------------------------------------------------------------------
    def __init__(self, generalSettings, settings, parent):
        """
        """
        super(DataSource2D, self).__init__(parent)

        self.settings = settings
        self.generalSettings = generalSettings

        self.log = logging.getLogger("cam_logger")  # is in sync with the main thread? TODO

        self._deviceProxy = None
        self._worker = None

        self._deviceID = self.settings.option("device", "name")

        # more options, better names TODO
        self._clipRect = generalSettings.node("vimbacam/clip").getAttribute("rect")  # "vimbcacam node TMP TODO
        self._clipRect = [int(v) for v in self._clipRect.split(",")]

        self._frameMutex = QtCore.QMutex()  # sync access to frame
        self._lastFrame = np.zeros((1, 1))

        self.vflip = self.settings.option("flip", "vertical") == "True"
        self.hflip = self.settings.option("flip", "horizontal") == "True"
        try:
            self.rotateAngle = np.floor_divide(int(self.settings.option("flip", "rotate")), 90)
        except:
            self.rotateAngle = 0


        self._state = "idle"

    # ----------------------------------------------------------------------
    def _resetWorker(self):
        """
        """
        if self._worker:
            self._state = 'abort'
            self._worker.join()

        self._worker = threading.Thread(target=self.run)

    # ----------------------------------------------------------------------
    def start(self):
        """
        """
        self._resetWorker()
        self._worker.start()

    # ----------------------------------------------------------------------
    def run(self):
        """
        """
        self._deviceProxy = self._initDeviceProxy()
        self._startAcquisition()

        while self.state() == "running":
            lastTime = time.time()
            if self.state() in ["abort", "idle"]:
                # print "aborting acq loop"
                break

            frame = self._deviceProxy.maybeReadFrame()
            if frame is not None:
                self._lastFrame = frame
                self.newFrame.emit()

            if self._deviceProxy.errorFlag:
                self.gotError.emit(str(self._deviceProxy.errorMsg))
                self._state = "abort"

            time.sleep(self.TICK)  # limits FPS!
        self.log.info("Closing {}...".format(self._deviceID))

        if self._deviceProxy:
            self._deviceProxy.stopAcquisition()

        self._changeState("idle")

    # ----------------------------------------------------------------------
    def _startAcquisition(self):
        """
        """
        if self._deviceProxy:
            self._deviceProxy.startAcquisition()
            self._changeState("running")

    # ----------------------------------------------------------------------
    def rotate(self):
        if self.vflip and self.hflip:
            self._lastFrame = self._lastFrame[::-1, ::-1]
        elif self.vflip:
            self._lastFrame = self._lastFrame[::, ::-1]
        elif self.hflip:
            self._lastFrame = self._lastFrame[::-1, :]

        if self.rotateAngle:
            self._lastFrame = np.rot90(self._lastFrame, self.rotateAngle)

    # ----------------------------------------------------------------------
    def stop(self):
        """
        """
        self.log.info("Stop {}...".format(self._deviceID))

        self._changeState("abort")
        time.sleep(2 * self.TICK)

    # ----------------------------------------------------------------------
    def getFrame(self, mode="copy"):
        """
        """
        # lock = QtCore.QMutexLocker(self._frameMutex)
        self.rotate()
        return self._lastFrame  #

    # ----------------------------------------------------------------------
    def _initDeviceProxy(self):
        """
        Returns:
            handle to (typically 2D) data source
        """
        try:
            proxyClass = self.settings.option("device", "proxy")
            self.log.info("Loading device proxy {}...".format(proxyClass))

            module = importlib.import_module("devices.{}".format(proxyClass.lower()))
            proxy = getattr(module, proxyClass)(self.settings, self.generalSettings, self.log)

            # proxy = VimbaProxy(tangoServer, deviceID, downRect, self.log)
            # self.log.info("Camera {} ({}) initialized".format(cameraID, tangoServer))

        except Exception as ex:
            self.log.error(ex)
            raise

        return proxy

    # ----------------------------------------------------------------------
    def state(self):
        """
        Args:
        """
        return self._state  # return proxy's state! TODO

    # ----------------------------------------------------------------------
    def _changeState(self, newState):
        """
        Args:
            (str) newState
        """
        self._state = newState

    # ? TODO
    # ----------------------------------------------------------------------
    def getParams(self):
        """As datasource...
        """
        totalCounts = np.sum(self._lastFrame)
        return totalCounts
