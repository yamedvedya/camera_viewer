#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de
# Last modified: 2017, December 11
# ----------------------------------------------------------------------

"""Dummy 2D data generator.
"""

import numpy as np

# ----------------------------------------------------------------------
class DummyProxy(object):
    """
    """
    FRAME_W = 2500
    FRAME_H = 2500

    NOISE = 0.27

    # ----------------------------------------------------------------------
    def __init__(self, settings, generalSettings,  log):
        super(DummyProxy, self).__init__()

        clipRect = generalSettings.option("clip", "rect").split(",")

        self.x1 = int(max(clipRect[0], 0))
        self.y1 = int(max(clipRect[1], 0))
        self.x2 = int(min(clipRect[2], self.FRAME_W))
        self.y2 = int(min(clipRect[3], self.FRAME_H))

        x, y = np.meshgrid(np.linspace(-4, 4, self.FRAME_W),
                           np.linspace(-4, 4, self.FRAME_H))
        x += 0.0
        y += -1.0

        mean, sigma = 0, 0.2
        self._baseData = np.exp(-((np.sqrt(x * x + y * y * 4) - mean) ** 2 /
                                ( 2.0 * sigma ** 2)))
        self.errorFlag = False
        self.errorMsg = ''
    
    # ----------------------------------------------------------------------
    def maybeReadFrame(self):
        """
        """
        nPoints = self.FRAME_W * self.FRAME_H
        data = self._baseData + np.random.uniform(0.0, self.NOISE, nPoints).reshape(self.FRAME_W, self.FRAME_H)

        return data[self.x1:self.x2, self.y1:self.y2]

    # ----------------------------------------------------------------------
    def startAcquisition(self):
        pass

    # ----------------------------------------------------------------------
    def stopAcquisition(self):
        pass

    # ----------------------------------------------------------------------
    def close(self):
        pass

