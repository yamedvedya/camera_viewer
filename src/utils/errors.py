#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de
# Last modified: 2017, October 2
# ----------------------------------------------------------------------

"""Errors related functionality
"""

import traceback

from PyQt4 import QtGui

# ----------------------------------------------------------------------
def report_error(err, log=None, parent=None, simplify=False):
    """Send error message to the logging object and show user-friendly
    dialog box.
    """
    if log:
        log.exception(err)

    if parent:
        msg = str(err) if simplify else "{}\n\n{}".format(str(err).capitalize(),
                                                          str(traceback.format_exc()))
        QtGui.QMessageBox.warning(parent, "Exception", msg,
                                  QtGui.QMessageBox.Ok)

    # TODO
    # more user friendly ErrorDialog

