#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de
# Last modified: 2018, February 2
# ----------------------------------------------------------------------

"""Readout last .nxs file produced by the detector and extract dataframe.
"""

from datetime import datetime

import h5py
import numpy as np

# ----------------------------------------------------------------------
class LambdaDetector(object):
    """
    """
    
    # ----------------------------------------------------------------------
    def __init__(self, settings, generalSettings, log):
        super(LambdaDetector, self).__init__()

        self.log = log

        self.data_dir = self.settings.option("device", "datadir")
        self.file_base = self.settings.option("device", "filebase")

        self._lastFile = datetime.now()
        
        self._newFlag = False
        self.errorFlag = False
        self.errorMsg = ''
        self._lastFrame = np.zeros((1, 1))

    # ----------------------------------------------------------------------
    def startAcquisition(self):
        pass

    # ----------------------------------------------------------------------
    def stopAcquisition(self):
        pass

    # ----------------------------------------------------------------------
    def close(self):
        pass


    # ----------------------------------------------------------------------
    def maybeReadFrame(self):
        """
        """
        filename = self._lastFilename()             # readout recently generated file
        if filename:
            f = h5py.File(filename, "r")
            frame = f["/entry/instrument/detector/data"][0]      # get the first frame?

            #sub_frame = frame[x:x + w, y:y + h]
            #print(sub_frame)
       
            self._lastFrame = frame
            self._newFlag = True

            return self._lastFrame

        return None
           
            #np.transpose(data.value)
            #self._lastFrame = np.copy(data.value)

    # ----------------------------------------------------------------------
    def _lastFilename(self):
        """
        """
        for name in os.listdir(self.data_dir):
            if name.endswith(".nxs"):                   # musi sie zgadzac z filebase
                fullPath = os.path.join(self.data_dir, name)
                fileDate = datetime.fromtimestamp(os.path.getmtime(fullPath))
                
                nTries = 3              # ?? th

                if fileDate > self._lastFileTime:
                    return fullPath

        return None

