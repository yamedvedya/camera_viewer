#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@mail.desy.de
# Last modified: 2017, November 7
# ----------------------------------------------------------------------

"""Basic info dialog
"""

from datetime import datetime
import os

from PyQt5 import QtWidgets

from src.gui.AboutDialog_ui import Ui_AboutDialog

# ----------------------------------------------------------------------
class AboutDialog(QtWidgets.QDialog):
    """
    """
    SOURCE_DIR = "src"
    DATETIME = "%Y-%m-%d %H:%M:%S"

    # ----------------------------------------------------------------------
    def __init__(self, parent):
        super(AboutDialog, self).__init__(parent)

        self._ui = Ui_AboutDialog()
        self._ui.setupUi(self)

        self._getModification()

    # ----------------------------------------------------------------------
    def _getModification(self):
        """Display last source code modification date.
        """
        mtime = 0

        for root, _, files in os.walk(self.SOURCE_DIR, topdown=True):
            for name in files:
                filename = os.path.join(root, name)
                _, ext = os.path.splitext(filename)

                if ext == ".py":
                    ftime = os.path.getmtime(filename)
                    if ftime > mtime:
                        mtime = ftime

        txt = datetime.fromtimestamp(mtime).strftime(self.DATETIME)
        self._ui.lbModified.setText("({})".format(txt))

