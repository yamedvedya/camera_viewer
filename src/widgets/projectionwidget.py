#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de
# Last modified: 2017, November 20
# ----------------------------------------------------------------------

"""Displays x/y projection of a data frame.
"""

import numpy as np

from PyQt4 import QtCore, QtGui

import pyqtgraph as pg

from src.ui_vimbacam.ProjectionWidget_ui import Ui_ProjectionWidget

# ----------------------------------------------------------------------
class ProjectionWidget(QtGui.QWidget):
    """
    """
    PLOT_COLOR = QtGui.QColor(80, 90, 210)
   
    cursor_moved = QtCore.Signal(float, float)
    
    # ----------------------------------------------------------------------
    def __init__(self, parent):
        """
        """
        super(ProjectionWidget, self).__init__(parent)         # ???? TODO

            # temp? TODO
        self.parent = parent    
       
        pg.setConfigOption("leftButtonPan", False)
        
        self._ui = Ui_ProjectionWidget()
        self._ui.setupUi(self)
      
            # 
        self._plotItem, self._plot = self._setup_plot()
        self._ui.graphicsView.setCentralItem(self._plotItem)


            # temp? TODO
#        self._ui.graphicsView.setYLink(self.parent._ui.imageView.view)

        
        self._plotItem.scene().sigMouseMoved.connect(self._mouse_moved)
        self._plotItem.scene().sigMouseClicked.connect(self._mouse_clicked)
 
    # ----------------------------------------------------------------------
    def range_changed(self, array, axis, roiRect):
        """
        """
        x, y, w, h = roiRect

        yVec = array.sum(axis=axis)
        if axis == 0:           # y-profile
            xVec = np.linspace(y, y + h, len(yVec)) #* (-1)
        else:
            xVec = np.linspace(x, x + w, len(yVec))

        self._plot.setData(xVec, yVec)

    # ----------------------------------------------------------------------
    def as_projection_y(self):
        """
        """
        self._plot.rotate(90)

        self._plot.getViewBox().invertY(True)
        #self._plot.getViewBox().invertX(True)

    # ----------------------------------------------------------------------
    def _mouse_moved(self, pos):
        """
        """
        if self._plotItem.sceneBoundingRect().contains(pos):
            pos = self._plotItem.vb.mapSceneToView(pos)
            self.cursor_moved.emit(pos.x(), pos.y())

    # ----------------------------------------------------------------------
    def _mouse_clicked(self, event):
        """
        """
        if event.double():
            self._plotItem.autoRange()

    # ----------------------------------------------------------------------
    def _setup_plot(self):
        """
        """
        item = pg.PlotItem()
        item.showGrid(True, True)
        item.setMenuEnabled(False)
        item.enableAutoScale()
    
        plot = item.plot([], pen=self.PLOT_COLOR, name="")
 
        return item, plot

