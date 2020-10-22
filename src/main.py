#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de
# Last modified: 2018, February 2
# ----------------------------------------------------------------------

"""
"""

# TODO:
# - rename the software

from __future__ import print_function

import sys
from optparse import OptionParser

from PyQt4 import QtGui

from src.mainwindow import MainWindow


# ----------------------------------------------------------------------
def onExit(appName):
    print(__name__, "{} closed properly".format(appName))

# ----------------------------------------------------------------------
def main():
    parser = OptionParser()

    parser.add_option("-b", "--beamlineID", dest="beamlineID",
                      help="Beamline identifier",
                      default="DESY_P23")
    parser.add_option("-i", "--config", dest="config",
                      help="Configuration file",
                      default="/home/p23user/utils/camera_viewer/config/camera_LM04.xml")

    (options, _) = parser.parse_args()

    app = QtGui.QApplication([])

    mainWindow = MainWindow(options)
    mainWindow.windowClosed.connect(onExit)
    mainWindow.show()

    sys.exit(app.exec_())

# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()

