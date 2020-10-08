#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de
# Last modified: 2017, December 5
# ----------------------------------------------------------------------

"""
"""

import logging
import time
from datetime import datetime

import numpy as np
import scipy.ndimage.measurements as scipymeasure

from PyQt4 import QtCore, QtGui

import pyqtgraph as pg
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients

from src.utils.errors import report_error
from src.utils.functions import roi_text

from src.devices.datasource2d import DataSource2D

from src.ui_vimbacam.FrameViewer_ui import Ui_FrameViewer
from settingswidget import SettingsWidget


# ----------------------------------------------------------------------
class FrameViewer(QtGui.QWidget):
    """
    """
    statusChanged = QtCore.Signal(float)
    roiChanged = QtCore.Signal(int, int, int, int, float, bool)
    roiStats = QtCore.Signal(tuple, tuple, int, tuple, int)
    cursorMoved = QtCore.Signal(float, float)
    deviceStarted = QtCore.Signal()
    deviceStopped = QtCore.Signal()

    DEFAULT_IMAGE_EXT = "png"
    FILE_STAMP = "%Y%m%d_%H%M%S"
    DATETIME = "%Y-%m-%d %H:%M:%S"

    LABEL_BRUSH = (30, 144, 255, 170)
    LABEL_COLOR = (255, 255, 255)

    MINLEVEL = 0
    MAXLEVEL = 1
    AUTORANGE = True
    COLORMAP = 'grey'

    MAXFPS = 2

    # ----------------------------------------------------------------------
    def __init__(self, generalSettings, settings, parent):
        """
        """
        super(FrameViewer, self).__init__(parent)

        self.log = logging.getLogger("cam_logger")

        self.generalSettings = generalSettings
        self.settings = settings

        self._deviceID = self.settings.option("device", "name")

        self._saveDataFolder = self.generalSettings.option("save_folder", "default")
        self._saveImageFolder = self.generalSettings.option("save_folder", "default")

        self._dataSource = None  # should frameviewer be the owner of the datasource?

        self._ui = Ui_FrameViewer()
        self._ui.setupUi(self)

        self._initUi()

        self._isFirstFrame = True  # temp TODO
        self._lastFrame = None
        self._darkFrame = None

        self._fps = 2.0
        self.threshold = 0

        self._acqStarted = time.time()
        self._nFrames = 0
        self.isAccumulating = True

        self._liveModeStatus = "idle"

        self._rectRoi = pg.RectROI([100, 100], [50, 50], pen=(0, 9))
        self._ui.imageView.view.addItem(self._rectRoi)
        self._rectRoi.sigRegionChanged.connect(self._roiChanged)
        self._rectRoi.hide()

        self.markers = []
        for marker in range(SettingsWidget.NUM_MARKERS):
            self.markers.append(ImageMarker(0, 0, self._ui.imageView))
            self.markers[marker].setVisible(False)

        self.crossItem = LineSegmentItem([0, 0], [0, 0])
        self.crossItem.setVisible(True)
        self._ui.imageView.view.addItem(self.crossItem)

        self.roiIntegral = 0.0

        self._ui.wiProfileX.cursorMoved.connect(lambda x, y: self.cursorMoved.emit(x, y))
        self._ui.wiProfileY.cursorMoved.connect(lambda x, y: self.cursorMoved.emit(x, y))

        #
        self._ui.wiProfileY.asProjectionY()

        self._ui.imageView.scene.sigMouseMoved.connect(self._mouseMoved)
        self._ui.imageView.scene.sigMouseClicked.connect(self._mouseClicked)
        self._ui.imageView.scene.sigMouseHover.connect(self._mouseHover)

        self._ui.imageView.view.sigRangeChanged.connect(self._visibleRangeChanged)
        self._ui.imageView.view.setMenuEnabled(False)

        # self._viewRect = viewBox.viewRect()

        self.visibleMarker = 'none'

        # a few info labels
        self._deviceLabel = self._addLabel(self._deviceID,
                                           self.generalSettings.node("vimbacam/title_label"),
                                           visible=True)
        self._datetimeLabel = self._addLabel("Time",
                                             self.generalSettings.node("vimbacam/datetime_label"),
                                             visible=True)
        self._roiLabel = self._addLabel("ROI",
                                        self.generalSettings.node("vimbacam/roi_label"),
                                        visible=False)

        self.x = 0
        self.y = 0
        self.log.info("Initialized successfully")

        # self._refreshTimer = QtCore.QTimer(self)
        # self._refreshTimer.timeout.connect(self._refreshView)
        # self._refreshTimer.start(1/self.MAXFPS)

        self.startStopLiveMode()

    # ----------------------------------------------------------------------
    def _initUi(self):
        """
        """
        self._ui.imageView.ui.histogram.hide()
        self._ui.imageView.ui.roiBtn.hide()
        self._ui.imageView.ui.menuBtn.hide()

    # ----------------------------------------------------------------------
    def updateMarker(self, num, x, y, visible):
        """
        Refresh marker's position (possibly many markers? TODO)
        """
        self.markers[num].setPos(x, y)
        self.markers[num].setVisible(visible)

    # ----------------------------------------------------------------------
    def updateRoi(self, x, y, w, h, threshold, visible):  # CS
        """ROI coords changed elsewhere.
        """
        self.blockSignals(True)
        self.roiVisible = visible
        self._rectRoi.setPos([x, y])
        self._rectRoi.setSize([w, h])

        self._rectRoi.setVisible(visible)
        self._roiLabel.setVisible(visible)

        self.threshold = threshold

        self.blockSignals(False)

    # ----------------------------------------------------------------------
    def _roiChanged(self, roiRect):
        """Called when ROI emits sigRegionChanged signal.
        """
        if self._lastFrame is not None:
            pos, size = roiRect.pos(), roiRect.size()
            x, y, w, h = pos.x(), pos.y(), size.x(), size.y()

            self.roiChanged.emit(x, y, w, h, self.threshold, self.roiVisible)

            self._redrawRoiLabel()

    # ----------------------------------------------------------------------
    def _visibleRangeChanged(self, viewBox):
        """
        """
        self._viewRect = viewBox.viewRect()

        if self._lastFrame is not None:
            start = time.time()

            self._redrawProjections()

            self._showTitle()
            self._showDatetime()
            self._redrawRoiLabel()
            # self.image_size_changed.emit(self._viewRect.x(), self._viewRect.y(), self._viewRect.width(),
            #                              self._viewRect.height())

    # ----------------------------------------------------------------------
    def _redrawProjections(self):
        """
        """
        epsilon = 10
        if (self._ui.wiProfileX.frameSize().height() < epsilon and
                self._ui.wiProfileY.frameSize().width() < epsilon):
            return

            # take into account current view range
        x, y = self._viewRect.x(), self._viewRect.y()
        w, h = self._viewRect.width(), self._viewRect.height()

        frameW, frameH = self._lastFrame.shape
        x, y = int(max(0, x)), int(max(0, y))
        w, h = int(min(w, frameW)), int(min(h, frameH))

        dataSlice = self._lastFrame[x:x + w, y:y + h]

        if self._ui.wiProfileX.frameSize().height() > epsilon:
            self._ui.wiProfileX.rangeChanged(dataSlice, 1, (x, y, w, h))

        if self._ui.wiProfileY.frameSize().width() > epsilon:
            self._ui.wiProfileY.rangeChanged(dataSlice, 0, (x, y, w, h))

    # ----------------------------------------------------------------------
    def startStopLiveMode(self):
        """
        """
        if not self._dataSource:
            self._dataSource = self._initDataSource()

        if (self._dataSource and
                self._dataSource.state() in ["idle", "abort"]):
            self.startLiveMode()

            self._acqStarted = time.time()
            self._nFrames = 0
        else:
            self.stopLiveMode()

    # ----------------------------------------------------------------------
    def startLiveMode(self):
        """
        """
        if self._dataSource:
            self._isFirstFrame = True  # TMP TODO

            self._dataSource.start()
            self.deviceStarted.emit()
        else:
            QtGui.QMessageBox.warning(self, "Initialization Error",
                                      "{} not yet initialized".format(self._deviceID))

    # ----------------------------------------------------------------------
    def stopLiveMode(self):
        """
        """
        if self._dataSource:
            self._dataSource.stop()
            self.log.debug("{} stopped".format(self._deviceID))

        self.deviceStopped.emit()

    # ----------------------------------------------------------------------
    def _initDataSource(self):
        """
        """
        try:
            dataSource = DataSource2D(self.generalSettings, self.settings, self)
            # self.image_size_changed.connect(dataSource.change_image_size)
            dataSource.newFrame.connect(self._refreshView)
            dataSource.gotError.connect(lambda errMsg: self._gotAnError(errMsg))
            return dataSource

        except Exception as err:
            report_error(err, self.log, self)
            return None

    # ----------------------------------------------------------------------
    def close(self):
        """
        """
        self.log.debug("Closing {0}".format(self._deviceID))

        if self._dataSource:
            self._dataSource.stop()

    def move_image(self, x,y,w,h):
        self.x = x
        self.y = y

    # ----------------------------------------------------------------------
    def _refreshView(self):
        """
        """
        spectrumColormap = pg.ColorMap(*zip(*Gradients[self.COLORMAP]["ticks"]))
        if self._isFirstFrame:
            # self._lastFrame = np.array(self._dataSource.getFrame("copy"), dtype=np.float)
            self._lastFrame = self._dataSource.getFrame("copy")
            self._ui.imageView.setImage(self._lastFrame, autoLevels=self.AUTORANGE,
                                        levels=(self.MINLEVEL, self.MAXLEVEL))
            self._ui.imageView.imageItem.setLookupTable(spectrumColormap.getLookupTable())
            self._isFirstFrame = False
        else:
            self._lastFrame = self._dataSource.getFrame("copy")
            if self._darkFrame is not None:
                valid_idx = self._lastFrame > self._darkFrame
                self._lastFrame[valid_idx] -= self._darkFrame[valid_idx]
                self._lastFrame[~valid_idx] = 0
            self._ui.imageView.imageItem.setImage(self._lastFrame, autoLevels=self.AUTORANGE,
                                                  levels=(self.MINLEVEL, self.MAXLEVEL))
            self._ui.imageView.imageItem.setX(self.x)
            self._ui.imageView.imageItem.setY(self.y)
            self._ui.imageView.imageItem.setLookupTable(spectrumColormap.getLookupTable())

            self._ui.imageView.repaint()

        # gotImage = time.time() - self._acqStarted

        self._showTitle()
        self._showDatetime()
        self._redrawRoiLabel()
        # roi = time.time() - self._acqStarted

        self._redrawProjections()

        # projections = time.time() - self._acqStarted

        # print('gotImage ' + '{:.2f}'.format(gotImage) + ' roi ' + '{:.2f}'.format(roi) + ' projections ' + '{:.2f}'.format(projections))

        self._nFrames += 1
        self._fps = 1. / (time.time() - self._acqStarted)
        self.statusChanged.emit(self._fps)

        self._acqStarted = time.time()
        # use recent measurement

    # ----------------------------------------------------------------------
    def _gotAnError(self, msg):
        mb = QtGui.QMessageBox("ERROR !", "Camera error: {}".format(msg),
                               QtGui.QMessageBox.Warning, QtGui.QMessageBox.Ok, 0, 0)
        mb.exec_()
        return
        # ----------------------------------------------------------------------

    # ----------------------------------------------------------------------
    def _showTitle(self):
        """
        """
        if hasattr(self, "_deviceLabel"):
            self._showLabel(0.5, 0.04, self._deviceLabel)

    # ----------------------------------------------------------------------
    def _showDatetime(self):
        """
        """
        if hasattr(self, "_datetimeLabel"):
            msg = datetime.now().strftime(self.DATETIME)
            self._datetimeLabel.setText(msg)

            self._showLabel(0.85, 0.9, self._datetimeLabel)

    # ----------------------------------------------------------------------
    def FWHM(self, Y):
        try:
            X = range(Y.size)
            half_max = (np.amax(Y) - np.amin(Y)) / 2
            # find when function crosses line half_max (when sign of diff flips)
            # take the 'derivative' of signum(half_max - Y[])
            diff = np.sign(Y - half_max)
            left_idx = np.where(diff > 0)[0][0]
            right_idx = np.where(diff > 0)[0][-1]
            # find the left and right most indexes

            return right_idx - left_idx  # return the difference (full width)
        except:
            return 0

    # ----------------------------------------------------------------------
    def roiMarkerSelected(self, visibleMarker):
        self.visibleMarker = visibleMarker

    # ----------------------------------------------------------------------
    def _redrawRoiLabel(self):
        """
        """
        if self._rectRoi.isVisible():
            pos, size = self._rectRoi.pos(), self._rectRoi.size()
            x, y, w, h = int(pos.x()), int(pos.y()), int(size.x()), int(size.y())

            array = self._lastFrame[x:x + w, y:y + h]
            if array != []:
                low_values_flags = array < self.threshold  # Where values are low
                array[low_values_flags] = 0  # All low values set to 0
                self.roiIntegral = np.sum(array)
                self.roiExtrema = scipymeasure.extrema(array)  # all in one!
                self.roiMinVal = self.roiExtrema[0]
                self.roiMaxVal = self.roiExtrema[1]
                self.roiCoM = scipymeasure.center_of_mass(array)
                try:
                    self.roiCoMval = array[int(round(self.roiCoM[0])), int(round(self.roiCoM[1]))]
                except:
                    self.roiCoMval = [0, 0]

                Y = np.sum(array, axis=0)
                X = np.sum(array, axis=1)
                self.roiFWHM = (self.FWHM(X), self.FWHM(Y))

                if self.visibleMarker == 'max':
                    # Marker on Max
                    self.crossItem.setPos((self.roiExtrema[3][0] + x, self.roiExtrema[3][1] + y), self.roiFWHM)
                    self.crossItem.setVisible(True)
                elif self.visibleMarker == 'min':
                    # Marker on Max
                    self.crossItem.setPos((self.roiExtrema[2][0] + x, self.roiExtrema[2][1] + y), self.roiFWHM)
                    self.crossItem.setVisible(True)
                elif self.visibleMarker == 'com':
                    # Marker auf CoM
                    self.crossItem.setPos((self.roiCoM[0] + x, self.roiCoM[1] + y), self.roiFWHM)
                    self.crossItem.setVisible(True)
                elif self.visibleMarker == 'none':
                    self.crossItem.setVisible(False)
                    # self.crossItem([0,0], [0,0])

                self.roiStats.emit(self.roiExtrema, (self.roiCoM[0] + x, self.roiCoM[1] + y), self.roiCoMval,
                                   self.roiFWHM,
                                   self.roiIntegral)
                self._roiLabel.setText(roi_text(self.roiIntegral, compact=False))

                self._showLabel(0.1, 0.9, self._roiLabel)  # hotspot based

    # ----------------------------------------------------------------------
    def _mouseMoved(self, pos):
        """
        """
        pos = self._ui.imageView.view.mapSceneToView(pos)
        self.cursorMoved.emit(pos.x(), pos.y())

    # ----------------------------------------------------------------------
    def _mouseClicked(self, event):
        """
        """
        if event.double():
            self._ui.imageView.autoRange()

    # ----------------------------------------------------------------------
    def _mouseHover(self, event):
        pass

        # if event.buttons():
        # self.stopLiveMode()

    # ----------------------------------------------------------------------
    def _addLabel(self, text, style=None, visible=True):
        """
        """
        if not style:
            color = self.LABEL_COLOR
            fill = self.LABEL_BRUSH
            font = QtGui.QFont("Arial", 10)
        else:
            color = tuple(int(v) for v in style.getAttribute("fg_color").split(","))
            fill = tuple(int(v) for v in style.getAttribute("bg_color").split(","))
            font = style.getAttribute("font").split(",")
            print("f:", font)
            font = QtGui.QFont(font[0], int(font[1]))

        item = pg.TextItem(text=text, color=color, fill=fill)
        item.setFont(font)
        item.setVisible(visible)

        self._ui.imageView.view.addItem(item)

        return item

    # ----------------------------------------------------------------------
    def _showLabel(self, x, y, label):
        """
        Args:
            x, y (float), normalized to 0-1 range position
        """
        [[xMin, xMax], [yMin, yMax]] = self._ui.imageView.view.viewRange()

        deltaX = abs(xMax - xMin)
        textX = xMax - deltaX * (1. - x)

        deltaY = abs(yMax - yMin)
        textY = yMax - deltaY * (1. - y)

        label.setPos(textX, textY)

    # ----------------------------------------------------------------------
    def saveToImage(self):
        """
        """
        self.stopLiveMode()

        fileName = self._getImageFileName("Save Image")
        if fileName:
            pixmap = QtGui.QPixmap.grabWidget(self._ui.imageView)
            pixmap.save(fileName)

    # ----------------------------------------------------------------------

    def saveToFile(self, fmt):
        """Saves to text file or numpy's npy/npz.
        """
        self.stopLiveMode()

        fmt = fmt.lower()
        defaultName = "data_{}.{}".format(datetime.now().strftime(self.FILE_STAMP),
                                          fmt)

        fileTuple = QtGui.QFileDialog.getSaveFileName(self, "Save To File", self._saveDataFolder + defaultName,
                                                      filter=(self.tr("Ascii Files (*.csv)")
                                                              if fmt == "csv" else
                                                              self.tr("Numpy Files (*.npy)")))

        self._saveDataFolder = QtCore.QFileInfo(fileTuple).path() + '/'

        fileName = str(fileTuple)
        fileName = fileName.strip()

        if fileName:
            data = self._dataSource.getFrame()  # sync with data acq! TODO

            if fmt.lower() == "csv":
                np.savetxt(fileName, data)
            elif fmt.lower() == "npy":
                np.save(fileName, data)
            else:
                raise ValueError("Unknown format '{}'".format(fmt))

    # ---------------------------------------------------------------------- 
    def printImage(self):
        """
        """
        self.stopLiveMode()

        self._printer = QtGui.QPrinter()

        if QtGui.QPrintDialog(self._printer).exec_() == QtGui.QDialog.Accepted:
            self._printPainter = QtGui.QPainter(self._printer)
            self._printPainter.setRenderHint(QtGui.QPainter.Antialiasing)

            self._ui.imageView.view.render(self._printPainter)

    # ---------------------------------------------------------------------- 
    def toClipboard(self):
        """NOTE that the content of the clipboard is cleared after program's exit.
        """
        self.stopLiveMode()

        pixmap = QtGui.QPixmap.grabWidget(self._ui.imageView)
        QtGui.qApp.clipboard().setPixmap(pixmap)

    # ----------------------------------------------------------------------
    def _getImageFileName(self, title):
        """
       """
        filesFilter = ";;".join(["(*.{})".format(ffilter) for ffilter in
                                 QtGui.QImageWriter.supportedImageFormats()])

        defaultName = "image_{}.{}".format(datetime.now().strftime(self.FILE_STAMP),
                                           self.DEFAULT_IMAGE_EXT)
        fileTuple = QtGui.QFileDialog.getSaveFileName(self, title, self._saveImageFolder + defaultName,
                                                      filesFilter,
                                                      selectedFilter="(*.{})".format(self.DEFAULT_IMAGE_EXT))

        self._saveImageFolder = QtCore.QFileInfo(fileTuple).path() + '/'

        return str(fileTuple)

    # ----------------------------------------------------------------------
    def saveUiSettings(self, settings):
        """
        Args:
            (QSettings)
        """
        settings.setValue("FrameViewer/splitterY1", self._ui.splitter_y1.saveState())
        settings.setValue("FrameViewer/splitterY2", self._ui.splitter_y2.saveState())
        settings.setValue("FrameViewer/splitterX", self._ui.splitter_x.saveState())

        settings.setValue("FrameViewer/geometry", self.saveGeometry())

    # ----------------------------------------------------------------------
    def loadUiSettings(self, settings):
        """
        Args:
            (QSettings)
        """
        self._ui.splitter_y1.restoreState(settings.value("FrameViewer/splitterY1").toByteArray())
        self._ui.splitter_y2.restoreState(settings.value("FrameViewer/splitterY2").toByteArray())
        self._ui.splitter_x.restoreState(settings.value("FrameViewer/splitterX").toByteArray())
        self.restoreGeometry(settings.value("FrameViewer/geometry").toByteArray())

    # ----------------------------------------------------------------------
    def enableAutoLevels(self, mode):
        self.AUTORANGE = mode

    # ----------------------------------------------------------------------
    def levelsChanged(self, min, max):
        self.MINLEVEL = min
        self.MAXLEVEL = max

    # ----------------------------------------------------------------------
    def colorMapChanged(self, selectedMap):
        if str(selectedMap) != '':
            self.COLORMAP = str(selectedMap)

    # ----------------------------------------------------------------------
    def set_dark_image(self):
        self._darkFrame = self._lastFrame

    # ----------------------------------------------------------------------
    def remove_dark_image(self):
        self._darkFrame = None

# ----------------------------------------------------------------------
class ImageMarker(object):
    """Infinite lines cross
    """

    # ----------------------------------------------------------------------
    def __init__(self, x, y, imageView):
        super(ImageMarker, self).__init__()

        self._markerV = pg.InfiniteLine(pos=x)
        imageView.addItem(self._markerV)

        self._markerH = pg.InfiniteLine(pos=y, angle=0)
        imageView.addItem(self._markerH)

    # ----------------------------------------------------------------------
    def setPos(self, x, y):
        """
        """
        self._markerV.setPos(x)
        self._markerH.setPos(y)

    # ----------------------------------------------------------------------
    def pos(self):
        """
        """
        return self._markerV.pos().x(), self._markerH.pos().y()

    # ----------------------------------------------------------------------
    def setVisible(self, flag):
        """
        """
        self._markerV.setVisible(flag)
        self._markerH.setVisible(flag)

    # ----------------------------------------------------------------------
    def visible(self):
        """
        """
        return self._markerV.isVisible() and self._markerH.isVisible()


# ----------------------------------------------------------------------
class LineSegmentItem(pg.GraphicsObject):
    def __init__(self, CoM, fwhm):
        pg.GraphicsObject.__init__(self)
        self.COM = CoM
        self.width = np.array(fwhm) / 2
        self.generatePicture()

    def setPos(self, CoM, fwhm):
        self.COM = CoM
        self.width = np.array(fwhm) / 2
        self.generatePicture()

    def generatePicture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen('r', width=2))
        # Horizontal
        p.drawLine(QtCore.QPoint(self.COM[0] - self.width[0], self.COM[1]),
                   QtCore.QPoint(self.COM[0] + self.width[0], self.COM[1]))
        # Vertical
        p.drawLine(QtCore.QPoint(self.COM[0], self.COM[1] - self.width[1]),
                   QtCore.QPoint(self.COM[0], self.COM[1] + self.width[1]))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())
