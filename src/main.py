# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------


"""
"""

import sys
from optparse import OptionParser

from PyQt5 import QtWidgets

from src.mainwindow import MainWindow


# ----------------------------------------------------------------------
def main():
    parser = OptionParser()

    parser.add_option("-b", "--beamlineID", dest="beamlineID",
                      help="Beamline identifier",
                      default="DESY_P23")

    (options, _) = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)

    mainWindow = MainWindow(options)
    mainWindow.show()

    return app.exec_()


# ----------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
