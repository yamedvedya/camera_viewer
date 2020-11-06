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
from src.utils.functions import roi_text

from src.ui_vimbacam.FrameViewer_ui import Ui_FrameViewer

# ----------------------------------------------------------------------
class FrameViewer(QtGui.QWidget):
    """
    """
    status_changed = QtCore.Signal(float)
    roi_changed = QtCore.Signal(int)
    roi_stats_ready = QtCore.Signal(int)
    cursor_moved = QtCore.Signal(float, float)
    device_started = QtCore.Signal()
    device_stopped = QtCore.Signal()

    DEFAULT_IMAGE_EXT = "png"
    FILE_STAMP = "%Y%m%d_%H%M%S"
    DATETIME = "%Y-%m-%d %H:%M:%S"

    LABEL_BRUSH = (30, 144, 255, 170)
    LABEL_COLOR = (255, 255, 255)

    min_level = 0
    max_level = 1
    auto_levels = True
    colormap = 'grey'

    MAXFPS = 2

    # ----------------------------------------------------------------------
    def __init__(self, settings, parent):
        """
        """
        super(FrameViewer, self).__init__(parent)

        self.log = logging.getLogger("cam_logger")

        self._settings = settings

        self._saveDataFolder = self._settings.option("save_folder", "default")
        self._saveImageFolder = self._settings.option("save_folder", "default")

        self._camera_device = None
        self._rois, self._markers, self._statistics = None, None, None
        self._current_roi_index = None

        self._ui = Ui_FrameViewer()
        self._ui.setupUi(self)

        self._init_ui()

        self._is_first_frame = True  # temp TODO
        self._last_frame = None
        self._dark_frame = None

        self._fps = 2.0

        self._acqStarted = time.time()
        self._nFrames = 0
        self.isAccumulating = True

        self._liveModeStatus = "idle"

        self._rectRoi = pg.RectROI([0, 0], [50, 50], pen=(0, 9))
        self._ui.imageView.view.addItem(self._rectRoi, ignoreBounds=True)
        self._rectRoi.sigRegionChanged.connect(self._roi_changed)
        self._rectRoi.hide()

        self._marker_widget = {}

        self.crossItem = LineSegmentItem([0, 0], [0, 0])
        self.crossItem.setVisible(True)
        self._ui.imageView.view.addItem(self.crossItem, ignoreBounds=True)

        self._ui.wiProfileX.cursor_moved.connect(lambda x, y: self.cursor_moved.emit(x, y))
        self._ui.wiProfileY.cursor_moved.connect(lambda x, y: self.cursor_moved.emit(x, y))

        #
        self._ui.wiProfileY.as_projection_y()

        self._ui.imageView.scene.sigMouseMoved.connect(self._mouse_moved)
        self._ui.imageView.scene.sigMouseClicked.connect(self._mouse_clicked)
        self._ui.imageView.scene.sigMouseHover.connect(self._mouse_hover)

        self._ui.imageView.view.sigRangeChanged.connect(self._visible_range_changed)
        self._ui.imageView.view.setMenuEnabled(False)

        self.visible_marker = 'none'

        # a few info labels
        self._deviceLabel = self._add_label('', self._settings.node("vimbacam/title_label"), visible=True)
        self._datetimeLabel = self._add_label("Time", self._settings.node("vimbacam/datetime_label"), visible=True)
        self._roiLabel = self._add_label("ROI", self._settings.node("vimbacam/roi_label"), visible=False)

        self.image_x_pos = 0
        self.image_y_pos = 0
        self.log.info("Initialized successfully")

    # ----------------------------------------------------------------------
    def _init_ui(self):
        """
        """
        self._ui.imageView.ui.histogram.hide()
        self._ui.imageView.ui.roiBtn.hide()
        self._ui.imageView.ui.menuBtn.hide()
        pass

    # ----------------------------------------------------------------------
    def set_variables(self, camera_device, rois, markers, statistics,current_roi_index):
        self._camera_device = camera_device
        self._rois = rois
        self._markers = markers
        self._statistics = statistics
        self._current_roi_index = current_roi_index

    # ----------------------------------------------------------------------
    def update_camera_label(self):

        self._deviceLabel.setText(self._camera_device.device_id)

    # ----------------------------------------------------------------------
    def markers_changed(self):
        for ind, widget in self._marker_widget.items():
            widget.delete_me()
            del self._marker_widget[ind]

        for ind, marker in self._markers.items():
            self._marker_widget[ind] = ImageMarker(self._markers[ind]['x'], self._markers[ind]['y'], self._ui.imageView)

    # ----------------------------------------------------------------------
    def update_marker(self, ind):

        self._marker_widget[ind].setPos(self._markers[ind]['x'], self._markers[ind]['y'])

    # ----------------------------------------------------------------------
    def update_roi(self, roi_index):  # CS
        """ROI coords changed elsewhere.
        """
        self._rectRoi.blockSignals(True)

        self._rectRoi.setVisible(self._rois[roi_index]['Roi_Visible'])
        self._roiLabel.setVisible(self._rois[roi_index]['Roi_Visible'])

        self._rectRoi.setPos([self._rois[roi_index]['RoiX'], self._rois[roi_index]['RoiY']])
        self._rectRoi.setSize([self._rois[roi_index]['RoiWidth'], self._rois[roi_index]['RoiHeight']])

        self._rectRoi.blockSignals(False)

    # ----------------------------------------------------------------------
    def _roi_changed(self, roiRect):
        """Called when ROI emits sigRegionChanged signal.
        """
        if self._last_frame is not None:
            pos, size = roiRect.pos(), roiRect.size()
            x = max(pos.x(), 0)
            y = max(pos.y(), 0)
            max_w, max_h = self._last_frame.shape

            w = min(size.x(), max_w - x)
            h = min(size.y(), max_h - y)

            self._rois[self._current_roi_index[0]]['RoiX'], self._rois[self._current_roi_index[0]]['RoiY']  = x, y
            self._rois[self._current_roi_index[0]]['RoiWidth'], self._rois[self._current_roi_index[0]]['RoiHeight'] = w, h

            self._redraw_roi_label()
            self.update_roi(self._current_roi_index[0])
            self.roi_changed.emit(self._current_roi_index[0])

    # ----------------------------------------------------------------------
    def _visible_range_changed(self, viewBox):
        """
        """
        self._viewRect = viewBox.viewRect()

        if self._last_frame is not None:

            self._redraw_projections()

            self._show_title()
            self._show_datetime()
            self._redraw_roi_label()

    # ----------------------------------------------------------------------
    def _redraw_projections(self):
        """
        """
        epsilon = 10
        if (self._ui.wiProfileX.frameSize().height() < epsilon and
                self._ui.wiProfileY.frameSize().width() < epsilon):
            return

        # take into account current view range
        x, y = self._viewRect.x(), self._viewRect.y()
        w, h = self._viewRect.width(), self._viewRect.height()

        frameW, frameH = self._last_frame.shape
        x, y = int(max(0, x)), int(max(0, y))
        w, h = int(min(w, frameW)), int(min(h, frameH))

        dataSlice = self._last_frame[x:x + w, y:y + h]

        if self._ui.wiProfileX.frameSize().height() > epsilon:
            self._ui.wiProfileX.range_changed(dataSlice, 1, (x, y, w, h))

        if self._ui.wiProfileY.frameSize().width() > epsilon:
            self._ui.wiProfileY.range_changed(dataSlice, 0, (x, y, w, h))

    # ----------------------------------------------------------------------
    def start_stop_live_mode(self):
        """
        """

        if (self._camera_device and
                self._camera_device.state() in ["idle", "abort"]):
            self.start_live_mode()

            self._acqStarted = time.time()
            self._nFrames = 0
        else:
            self.stop_live_mode()

    # ----------------------------------------------------------------------
    def start_live_mode(self):
        """
        """
        if self._camera_device:
            self._is_first_frame = True  # TMP TODO

            self._camera_device.start()
            self.device_started.emit()
        else:
            QtGui.QMessageBox.warning(self, "Initialization Error",
                                      "{} not yet initialized".format(self._camera_device.device_id))

    # ----------------------------------------------------------------------
    def stop_live_mode(self):
        """
        """
        if self._camera_device:
            self._camera_device.stop()
            self.log.debug("{} stopped".format(self._camera_device.device_id))

        self.device_stopped.emit()

    # ----------------------------------------------------------------------
    def close(self):
        """
        """
        self.log.debug("Closing {0}".format(self._camera_device.device_id))

        if self._camera_device:
            self._camera_device.stop()

    # ----------------------------------------------------------------------
    def move_image(self, x, y, w, h):

        self.image_x_pos = x
        self.image_y_pos = y

    # ----------------------------------------------------------------------
    def refresh_view(self):
        """
        """
        spectrum_colormap = pg.ColorMap(*zip(*Gradients[self.colormap]["ticks"]))

        self._last_frame = self._camera_device.get_frame("copy")
        if self._dark_frame is not None:
            valid_idx = self._last_frame > self._dark_frame
            self._last_frame[valid_idx] -= self._dark_frame[valid_idx]
            self._last_frame[~valid_idx] = 0

        if self.auto_levels:
            self._ui.imageView.setImage(self._last_frame, autoLevels=True, autoRange=False)
        else:
            self._ui.imageView.setImage(self._last_frame, levels=(self.min_level, self.max_level), autoRange=False)

        self._ui.imageView.imageItem.setLookupTable(spectrum_colormap.getLookupTable())
        self._ui.imageView.imageItem.setX(self.image_x_pos)
        self._ui.imageView.imageItem.setY(self.image_y_pos)

        if self._is_first_frame:
            self._is_first_frame = False
        else:
            self._ui.imageView.repaint()

        self._show_title()
        self._show_datetime()
        self._redraw_roi_label()
        self._redraw_projections()

        self._nFrames += 1
        self._fps = 1. / (time.time() - self._acqStarted)
        self.status_changed.emit(self._fps)

        self._acqStarted = time.time()

    # ----------------------------------------------------------------------
    def _show_title(self):
        """
        """
        if hasattr(self, "_deviceLabel"):
            self._show_label(0.5, 0.04, self._deviceLabel)

    # ----------------------------------------------------------------------
    def _show_datetime(self):
        """
        """
        if hasattr(self, "_datetimeLabel"):
            msg = datetime.now().strftime(self.DATETIME)
            self._datetimeLabel.setText(msg)

            self._show_label(0.85, 0.9, self._datetimeLabel)

    # ----------------------------------------------------------------------
    def FWHM(self, data):
        try:
            half_max = (np.amax(data) - np.amin(data)) / 2

            diff = np.sign(data - half_max)
            left_idx = np.where(diff > 0)[0][0]
            right_idx = np.where(diff > 0)[0][-1]
            return right_idx - left_idx  # return the difference (full width)
        except:
            return 0

    # ----------------------------------------------------------------------
    def roi_marker_selected(self, visible_marker):
        self.visible_marker = visible_marker

    # ----------------------------------------------------------------------
    def _redraw_roi_label(self):
        """
        """
        if self._rois[self._current_roi_index[0]]['Roi_Visible']:
            pos, size = self._rectRoi.pos(), self._rectRoi.size()
            x, y, w, h = int(pos.x()), int(pos.y()), int(size.x()), int(size.y())

            array = self._last_frame[x:x + w, y:y + h]
            if array != []:
                array[array < self._rois[self._current_roi_index[0]]['Threshold']] = 0  # All low values set to 0

                roi_sum = np.sum(array)

                try:
                    roiExtrema = scipymeasure.extrema(array)  # all in one!
                except:
                    roiExtrema = (0, 0, (0, 0), (0, 0))

                roi_max = (roiExtrema[3][0] + x, roiExtrema[3][1] + y)
                roi_min = (roiExtrema[2][0] + x, roiExtrema[2][1] + y)

                try:
                    roi_com = scipymeasure.center_of_mass(array)
                except:
                    roi_com = (0, 0)

                roi_com = (roi_com[0] + x, roi_com[1] + y)

                try:
                    intensity_at_com = self._last_frame[int(round(roi_com[0])), int(round(roi_com[1]))]
                except:
                    intensity_at_com = [0, 0]

                roi_FWHM = (self.FWHM(np.sum(array, axis=1)), self.FWHM(np.sum(array, axis=0)))

                if self.visible_marker == 'max':
                    # Marker on Max
                    self.crossItem.setPos(roi_max, roi_FWHM)
                    self.crossItem.setVisible(True)
                elif self.visible_marker == 'min':
                    # Marker on Max
                    self.crossItem.setPos(roi_min, roi_FWHM)
                    self.crossItem.setVisible(True)
                elif self.visible_marker == 'com':
                    # Marker auf CoM
                    self.crossItem.setPos(roi_com, roi_FWHM)
                    self.crossItem.setVisible(True)
                elif self.visible_marker == 'none':
                    self.crossItem.setVisible(False)
                    # self.crossItem([0,0], [0,0])

                self._statistics[self._current_roi_index[0]] = {"extrema": (roiExtrema[0], roiExtrema[1], roi_min, roi_max),
                                                              "com_pos" : roi_com,
                                                              "intensity_at_com": intensity_at_com,
                                                              'fwhm': roi_FWHM,
                                                              'sum': roi_sum}

                self.roi_stats_ready.emit(self._current_roi_index[0])
                self._roiLabel.setText(roi_text(roi_sum, compact=False))

                self._show_label(0.1, 0.9, self._roiLabel)  # hotspot based
    # ----------------------------------------------------------------------
    def _mouse_moved(self, pos):
        """
        """
        pos = self._ui.imageView.view.mapSceneToView(pos)
        self.cursor_moved.emit(pos.x(), pos.y())

    # ----------------------------------------------------------------------
    def _mouse_clicked(self, event):
        """
        """
        if event.double():
            self._ui.imageView.autoRange()

    # ----------------------------------------------------------------------
    def _mouse_hover(self, event):
        pass

        # if event.buttons():
        # self.stopLiveMode()

    # ----------------------------------------------------------------------
    def _add_label(self, text, style=None, visible=True):
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

        self._ui.imageView.view.addItem(item, ignoreBounds=True)

        return item

    # ----------------------------------------------------------------------
    def _show_label(self, x, y, label):
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
    def save_to_image(self):
        """
        """
        self.stop_live_mode()

        fileName = self._get_image_file_name("Save Image")
        if fileName:
            pixmap = QtGui.QPixmap.grabWidget(self._ui.imageView)
            pixmap.save(fileName)

    # ----------------------------------------------------------------------

    def save_to_file(self, fmt):
        """Saves to text file or numpy's npy/npz.
        """
        self.stop_live_mode()

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
            data = self._camera_device.get_frame()  # sync with data acq! TODO

            if fmt.lower() == "csv":
                np.savetxt(fileName, data)
            elif fmt.lower() == "npy":
                np.save(fileName, data)
            else:
                raise ValueError("Unknown format '{}'".format(fmt))

    # ---------------------------------------------------------------------- 
    def print_image(self):
        """
        """
        self.stop_live_mode()

        self._printer = QtGui.QPrinter()

        if QtGui.QPrintDialog(self._printer).exec_() == QtGui.QDialog.Accepted:
            self._printPainter = QtGui.QPainter(self._printer)
            self._printPainter.setRenderHint(QtGui.QPainter.Antialiasing)

            self._ui.imageView.view.render(self._printPainter)

    # ---------------------------------------------------------------------- 
    def to_clipboard(self):
        """NOTE that the content of the clipboard is cleared after program's exit.
        """
        self.stop_live_mode()

        pixmap = QtGui.QPixmap.grabWidget(self._ui.imageView)
        QtGui.qApp.clipboard().setPixmap(pixmap)

    # ----------------------------------------------------------------------
    def _get_image_file_name(self, title):
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
    def save_ui_settings(self, settings):
        """
        Args:
            (QSettings)
        """
        settings.setValue("FrameViewer/splitterY1", self._ui.splitter_y1.saveState())
        settings.setValue("FrameViewer/splitterY2", self._ui.splitter_y2.saveState())
        settings.setValue("FrameViewer/splitterX", self._ui.splitter_x.saveState())

        settings.setValue("FrameViewer/geometry", self.saveGeometry())

    # ----------------------------------------------------------------------
    def load_ui_settings(self, settings):
        """
        Args:
            (QSettings)
        """
        self._ui.splitter_y1.restoreState(settings.value("FrameViewer/splitterY1").toByteArray())
        self._ui.splitter_y2.restoreState(settings.value("FrameViewer/splitterY2").toByteArray())
        self._ui.splitter_x.restoreState(settings.value("FrameViewer/splitterX").toByteArray())
        self.restoreGeometry(settings.value("FrameViewer/geometry").toByteArray())

    # ----------------------------------------------------------------------
    def enable_auto_levels(self, mode):

        self.auto_levels = mode

    # ----------------------------------------------------------------------
    def levels_changed(self, min, max):

        self.min_level = min
        self.max_level = max

    # ----------------------------------------------------------------------
    def color_map_changed(self, selectedMap):
        if str(selectedMap) != '':
            self.colormap = str(selectedMap)

    # ----------------------------------------------------------------------
    def set_dark_image(self):
        self._dark_frame = self._last_frame

    # ----------------------------------------------------------------------
    def remove_dark_image(self):
        self._dark_frame = None

# ----------------------------------------------------------------------
class ImageMarker(object):
    """Infinite lines cross
    """

    # ----------------------------------------------------------------------
    def __init__(self, x, y, imageView):
        super(ImageMarker, self).__init__()

        self.imageView = imageView

        self._markerV = pg.InfiniteLine(pos=x)
        self.imageView.addItem(self._markerV, ignoreBounds=True)

        self._markerH = pg.InfiniteLine(pos=y, angle=0)
        self.imageView.addItem(self._markerH, ignoreBounds=True)

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
    def delete_me(self):
        self.imageView.removeItem(self._markerH)
        self.imageView.removeItem(self._markerV)

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
