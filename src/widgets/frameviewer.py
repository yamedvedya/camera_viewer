# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""

import logging
import time
from datetime import datetime
import json
import math

import numpy as np
import scipy.ndimage.measurements as scipymeasure
try:
    from skimage.feature import peak_local_max
except:
    pass
from src.utils.errors import report_error

from PyQt5 import QtCore, QtWidgets, QtGui, QtPrintSupport
from src.utils.functions import rotate

import pyqtgraph as pg
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
from src.utils.functions import roi_text

from src.ui_vimbacam.FrameViewer_ui import Ui_FrameViewer

# ----------------------------------------------------------------------
class FrameViewer(QtWidgets.QWidget):
    """
    """
    status_changed = QtCore.pyqtSignal(float)
    roi_changed = QtCore.pyqtSignal(int)
    roi_stats_ready = QtCore.pyqtSignal(int)
    cursor_moved = QtCore.pyqtSignal(float, float)
    range_changed = QtCore.pyqtSignal(float, float, float, float)
    new_auto_levels  = QtCore.pyqtSignal(int, int)

    DEFAULT_IMAGE_EXT = "png"
    FILE_STAMP = "%Y%m%d_%H%M%S"
    DATETIME = "%Y-%m-%d %H:%M:%S"

    LABEL_BRUSH = (30, 144, 255, 170)
    LABEL_COLOR = (255, 255, 255)

    min_level = 0
    max_level = 1
    auto_levels = True

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

        self._peak_markers = PeakMarker()
        self._peak_search = False
        self._peak_threshold = 80
        self._peak_search_mode = False
        self._ui.imageView.view.addItem(self._peak_markers, ignoreBounds=True)

        self._action_first_point = QtWidgets.QAction('Center search start', self)
        self._action_second_point = QtWidgets.QAction('Set second point', self)
        self._action_second_point.setVisible(False)
        self._action_clear_points = QtWidgets.QAction('Clear points', self)
        self._action_clear_points.setEnabled(False)

        self._context_menu = QtWidgets.QMenu()
        self._context_menu.addAction(self._action_first_point)
        self._context_menu.addAction(self._action_second_point)
        self._context_menu.addAction(self._action_clear_points)

        self._center_search_points = [None, None]
        self._search_in_progress = False

        self._is_first_frame = True  # temp TODO
        self._last_frame = None

        self.color_map_changed('grey')

        self._fps = 2.0
        self._viewRect = None

        self._acq_started = None
        self._n_frames = 0
        self._need_to_refresh_image = True

        self._rectRoi = pg.RectROI([0, 0], [50, 50], pen=(0, 9))
        self._ui.imageView.view.addItem(self._rectRoi, ignoreBounds=True)
        self._rectRoi.sigRegionChanged.connect(self._roi_changed)
        self._rectRoi.hide()

        self._marker_widgets = []

        self._cross_item = LineSegmentItem('cross')
        self._cross_item.setVisible(False)
        self._ui.imageView.view.addItem(self._cross_item, ignoreBounds=True)

        self._center_search_item = LineSegmentItem('center', float(self._settings.option("center_search", "cross")),
                                                    int(self._settings.option("center_search", "circle")))
        self._center_search_item.setVisible(False)
        self._ui.imageView.view.addItem(self._center_search_item, ignoreBounds=True)

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
        self._deviceLabel = self._add_label('', self._settings.node("camera_viewer/title_label"), visible=True)
        self._datetimeLabel = self._add_label("Time", self._settings.node("camera_viewer/datetime_label"), visible=True)
        self._roiLabel = self._add_label("ROI", self._settings.node("camera_viewer/roi_label"), visible=False)
        self._load_label = self._add_label("Load image", self._settings.node("camera_viewer/datetime_label"), visible=False)

        self._image_x_pos = 0
        self._image_y_pos = 0
        self._image_scale = (1, 1)
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
    def set_new_camera(self):
        self._need_to_refresh_image = True
        center_search = self._camera_device.get_settings('center_search', str)
        if center_search != '':
            coordinates = json.loads(center_search)
            if coordinates[0] is not None and coordinates[1] is not None and \
                coordinates[2] is not None and coordinates[3] is not None:

                self._center_search_points = [QtCore.QPointF(coordinates[0], coordinates[1]),
                                              QtCore.QPointF(coordinates[2], coordinates[3])]
                self._action_second_point.setVisible(False)
                self._action_clear_points.setEnabled(True)
                self._center_search_item.setVisible(True)
                self._display_center_search()

                return True

        # self._action_second_point.setVisible(False)
        self._action_clear_points.setEnabled(False)
        self._center_search_item.setVisible(False)
        self._display_center_search()
        self.refresh_view()

        return True
    # ----------------------------------------------------------------------
    def update_camera_label(self):

        self._deviceLabel.setText(self._camera_device.device_id)

    # ----------------------------------------------------------------------
    def markers_changed(self):
        for widget in self._marker_widgets:
            widget.delete_me()

        self._marker_widgets = []
        for ind, marker in enumerate(self._markers):
            self._marker_widgets.append(ImageMarker(marker['x'], marker['y'], self._ui.imageView))

    # ----------------------------------------------------------------------
    def update_marker(self, ind):

        self._marker_widgets[ind].setPos(self._markers[ind]['x'], self._markers[ind]['y'])

    # ----------------------------------------------------------------------
    def update_roi(self, roi_index):
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

            w = min(size.x(), max_w)
            h = min(size.y(), max_h)

            self._rois[self._current_roi_index[0]]['RoiX'], self._rois[self._current_roi_index[0]]['RoiY'] = x, y
            self._rois[self._current_roi_index[0]]['RoiWidth'], self._rois[self._current_roi_index[0]]['RoiHeight'] = w, h

            self._redraw_roi_label()
            self.update_roi(self._current_roi_index[0])
            self.roi_changed.emit(self._current_roi_index[0])

    # ----------------------------------------------------------------------
    def _visible_range_changed(self, viewBox):
        """
        """
        self._viewRect = viewBox.viewRect()

        self._peak_markers.new_scale(self._viewRect.width(), self._viewRect.height())
        self._center_search_item.new_scale(self._viewRect.width(), self._viewRect.height())

        if self._last_frame is not None:

            self._redraw_projections()

            self._show_labels()
            self._redraw_roi_label()

    # ----------------------------------------------------------------------
    def peak_search_modified(self, state, mode, threshold):

        self._peak_search = state
        self._peak_threshold = threshold
        self._peak_search_mode = mode
        self.refresh_view()

    # ----------------------------------------------------------------------
    def _find_peaks(self):
        if self._peak_search:
            try:
                if self._peak_search_mode:
                    coordinates = peak_local_max(self._last_frame, threshold_rel=self._peak_threshold/100)
                else:
                    coordinates = peak_local_max(self._last_frame, threshold_abs=self._peak_threshold)

                if len(coordinates) > 100:
                    report_error('Too many ({}) peaks found. Adjust the threshold'.format(len(coordinates)),
                                 self.log, self, True)
                    coordinates = ()
            except:
                coordinates = ()
        else:
            coordinates = ()

        self._peak_markers.new_peaks(coordinates)

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
        if self._camera_device and not self._camera_device.is_running():
            self._start_live_mode()
        else:
            self.stop_live_mode()

    # ----------------------------------------------------------------------
    def _start_live_mode(self):
        """
        """
        if self._camera_device:
            self._is_first_frame = True  # TMP TODO
            self._acq_started = time.time()
            self._n_frames = 0
            self._need_to_refresh_image = True
            self._camera_device.start()
        else:
            QtWidgets.QMessageBox.warning(self, "Initialization Error",
                                      "{} not yet initialized".format(self._camera_device.device_id))

    # ----------------------------------------------------------------------
    def stop_live_mode(self):
        """
        """
        if self._camera_device and self._camera_device.is_running():
            self._camera_device.stop()
            self.log.debug("{} stopped".format(self._camera_device.device_id))

    # ----------------------------------------------------------------------
    def close(self):
        """
        """
        self.log.debug("Closing FrameViewer")

        if self._camera_device and self._camera_device.is_running():
            self._camera_device.stop()
            
        super(FrameViewer, self).close()

    # ----------------------------------------------------------------------
    def move_image(self, x, y, w, h):

        self._image_x_pos = x
        self._image_y_pos = y
        self._need_to_refresh_image = True

    # ----------------------------------------------------------------------
    def scale_image(self, scale):
        self._image_scale = (scale, scale)
        self._need_to_refresh_image = True

    # ----------------------------------------------------------------------
    def refresh_view(self):
        """
        """
        if hasattr(self, "_load_label"):
            self._load_label.setVisible(True)

        try:
            self._last_frame = self._camera_device.get_frame("copy")

            set_kwargs = {'pos': (self._image_x_pos, self._image_y_pos),
                          'scale': self._image_scale}

            if self.auto_levels:
                set_kwargs['autoRange'] = True
                update_kwargs = {'autoLevels': True}
            else:
                set_kwargs['levels'] = (self.min_level, self.max_level)
                update_kwargs = {'levels': (self._image_x_pos, self._image_y_pos)}

            if self._need_to_refresh_image:
                self._ui.imageView.setImage(self._last_frame, **set_kwargs)
                self._need_to_refresh_image = False
            else:
                self._ui.imageView.imageItem.updateImage(self._last_frame, **update_kwargs)

            # if self._is_first_frame:
            #     self._is_first_frame = False
            # else:
            #     self._ui.imageView.repaint()

            self._peak_markers.new_scale(self._viewRect.width(), self._viewRect.height())
            self._center_search_item.new_scale(self._viewRect.width(), self._viewRect.height())

            self._show_labels()
            self._redraw_roi_label()
            self._redraw_projections()
            self._find_peaks()
            self.update_camera_label()

            self._n_frames += 1
            if time.time() - self._acq_started > 1:
                self.status_changed.emit(self._n_frames)
                self._n_frames = 0
                self._acq_started = time.time()

            if self.auto_levels:
                self.new_auto_levels.emit(int(self._ui.imageView.levelMin), int(self._ui.imageView.levelMax))

        except:
            pass

        if hasattr(self, "_load_label"):
            self._load_label.setVisible(False)

    # ----------------------------------------------------------------------
    def _show_labels(self):
        """
        """
        if hasattr(self, "_deviceLabel"):
            self._show_label(0.5, 0.04, self._deviceLabel)

        if hasattr(self, "_datetimeLabel"):
            msg = datetime.now().strftime(self.DATETIME)
            self._datetimeLabel.setText(msg)

            self._show_label(0.85, 0.9, self._datetimeLabel)

        if hasattr(self, "_load_label"):
            self._show_label(0.85, 0.04, self._load_label)

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
            x, y, w, h = int(pos.x() - self._image_x_pos), int(pos.y() - self._image_y_pos), int(size.x()), int(size.y())

            array = self._last_frame[x:x + w, y:y + h]
            if array != []:
                array[array < self._rois[self._current_roi_index[0]]['Threshold']] = 0  # All low values set to 0

                roi_sum = np.sum(array)

                try:
                    roiExtrema = scipymeasure.extrema(array)  # all in one!
                except:
                    roiExtrema = (0, 0, (0, 0), (0, 0))

                roi_max = (roiExtrema[3][0] + x + self._image_x_pos, roiExtrema[3][1] + y + self._image_y_pos)
                roi_min = (roiExtrema[2][0] + x + self._image_x_pos, roiExtrema[2][1] + y + self._image_y_pos)

                try:
                    roi_com = scipymeasure.center_of_mass(array)
                except:
                    roi_com = (0, 0)

                if math.isnan(roi_com[0]) or math.isnan(roi_com[1]):
                    roi_com = (0, 0)

                roi_com = (roi_com[0] + x + self._image_x_pos, roi_com[1] + y + self._image_y_pos)

                try:
                    intensity_at_com = self._last_frame[int(round(roi_com[0])), int(round(roi_com[1]))]
                except:
                    intensity_at_com = [0, 0]

                roi_FWHM = (self.FWHM(np.sum(array, axis=1)), self.FWHM(np.sum(array, axis=0)))

                if self.visible_marker == 'max':
                    # Marker on Max
                    self._cross_item.set_pos(roi_max, roi_FWHM)
                    self._cross_item.setVisible(True)
                elif self.visible_marker == 'min':
                    # Marker on Max
                    self._cross_item.set_pos(roi_min, roi_FWHM)
                    self._cross_item.setVisible(True)
                elif self.visible_marker == 'com':
                    # Marker auf CoM
                    self._cross_item.set_pos(roi_com, roi_FWHM)
                    self._cross_item.setVisible(True)
                elif self.visible_marker == 'none':
                    self._cross_item.setVisible(False)
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
        if self._search_in_progress:
            self._center_search_points[1] = pos
            self._display_center_search()

    # ----------------------------------------------------------------------
    def _mouse_clicked(self, event):
        """
        """
        if event.double():
            try:
                self._ui.imageView.autoRange()
            except:
                pass

        elif event.button() == 2:

            action = self._context_menu.exec_(event._screenPos)

            if action == self._action_first_point:
                self._center_search_points[0] = self._ui.imageView.view.mapSceneToView(event.scenePos())
                self._search_in_progress = True
                self._action_second_point.setVisible(True)
                self._action_clear_points.setEnabled(True)
                self._center_search_item.setVisible(True)
            elif action == self._action_second_point:
                self._center_search_points[1] = self._ui.imageView.view.mapSceneToView(event.scenePos())
                self._action_second_point.setVisible(False)
                self._search_in_progress = False
                self._save_center_search()
            else:

                self._center_search_points = [None, None]
                self._action_second_point.setVisible(False)
                self._action_clear_points.setEnabled(False)
                self._center_search_item.setVisible(False)
                self._search_in_progress = False
                self._save_center_search()

        elif event.button() == 1 and self._search_in_progress:
            self._center_search_points[1] = self._ui.imageView.view.mapSceneToView(event.scenePos())
            self._action_second_point.setVisible(False)
            self._search_in_progress = False
            self._save_center_search()

        self._display_center_search()

    # ----------------------------------------------------------------------
    def _save_center_search(self):
        if self._center_search_points[0] is not None and self._center_search_points[1] is not None:
            coordinates = [self._center_search_points[0].x(), self._center_search_points[0].y(),
                           self._center_search_points[1].x(), self._center_search_points[1].y()]
        else:
            coordinates = [None, None]
        self._camera_device.save_settings('center_search', json.dumps(coordinates))

    # ----------------------------------------------------------------------
    def _display_center_search(self):
        self._center_search_item.set_pos(self._center_search_points)

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
            pixmap = QtGui.QScreen.grabWidget(self._ui.imageView)
            pixmap.save(fileName)

    # ----------------------------------------------------------------------

    def save_to_file(self, fmt):
        """Saves to text file or numpy's npy/npz.
        """
        self.stop_live_mode()

        fmt = fmt.lower()
        defaultName = "data_{}.{}".format(datetime.now().strftime(self.FILE_STAMP),
                                          fmt)

        fileTuple, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save To File", self._saveDataFolder + defaultName,
                                                      filter=(self.tr("Ascii Files (*.csv)")
                                                              if fmt == "csv" else
                                                              self.tr("Numpy Files (*.npy)")))

        self._saveDataFolder = QtCore.QFileInfo(fileTuple).path() + '/'

        fileName = str(fileTuple)
        fileName = fileName.strip()

        if fileName:
            data, scale = self._camera_device.get_frame()  # sync with data acq! TODO

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

        self._printer = QtPrintSupport.QPrinter()

        if QtPrintSupport.QPrintDialog(self._printer).exec_() == QtWidgets.QDialog.Accepted:
            self._printPainter = QtGui.QPainter(self._printer)
            self._printPainter.setRenderHint(QtGui.QPainter.Antialiasing)

            self._ui.imageView.view.render(self._printPainter)

    # ---------------------------------------------------------------------- 
    def to_clipboard(self):
        """NOTE that the content of the clipboard is cleared after program's exit.
        """
        self.stop_live_mode()

        pixmap = QtGui.QScreen.grabWidget(self._ui.imageView)
        QtWidgets.qApp.clipboard().setPixmap(pixmap)

    # ----------------------------------------------------------------------
    def _get_image_file_name(self, title):
        """
       """
        filesFilter = ";;".join(["(*.{})".format(ffilter) for ffilter in
                                 QtGui.QImageWriter.supportedImageFormats()])

        defaultName = "image_{}.{}".format(datetime.now().strftime(self.FILE_STAMP),
                                           self.DEFAULT_IMAGE_EXT)
        fileTuple, _ = QtWidgets.QFileDialog.getSaveFileName(self, title, self._saveImageFolder + defaultName,
                                                      filesFilter)

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
        try:
            self._ui.splitter_y1.restoreState(settings.value("FrameViewer/splitterY1"))
        except:
            pass

        try:
            self._ui.splitter_y2.restoreState(settings.value("FrameViewer/splitterY2"))
        except:
            pass

        try:
            self._ui.splitter_x.restoreState(settings.value("FrameViewer/splitterX"))
        except:
            pass

        try:
            self.restoreGeometry(settings.value("FrameViewer/geometry"))
        except:
            pass

    # ----------------------------------------------------------------------
    def enable_auto_levels(self, mode):

        self.auto_levels = mode
        self.refresh_view()

    # ----------------------------------------------------------------------
    def levels_changed(self, min, max):

        self.min_level = min
        self.max_level = max
        self.refresh_view()

    # ----------------------------------------------------------------------
    def color_map_changed(self, selected_map):
        if str(selected_map) != '':
            colormap = str(selected_map)
        else:
            colormap = 'gray'

        self._ui.imageView.imageItem.setLookupTable(pg.ColorMap(*zip(*Gradients[colormap]["ticks"])).getLookupTable())
        self.refresh_view()

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
class PeakMarker(pg.GraphicsObject):
    """
        Circle object
    """

    # ----------------------------------------------------------------------
    def __init__(self):
        super(PeakMarker, self).__init__()
        pg.GraphicsObject.__init__(self)
        self._picture = QtGui.QPicture()
        self._positions = ()
        self._size = 0

    # ----------------------------------------------------------------------
    def new_peaks(self, positions):
        self._positions = positions
        self._draw()

    # ----------------------------------------------------------------------
    def new_scale(self, picture_w, picture_h):
        self._size = int(0.01*min(picture_w, picture_h))
        self._draw()

    # ----------------------------------------------------------------------
    def _draw(self):

        p = QtGui.QPainter(self._picture)
        p.setPen(pg.mkPen('r', width=2))

        for x, y in self._positions:
            p.drawEllipse(QtCore.QPoint(x, y), self._size, self._size)

        p.end()

    # ----------------------------------------------------------------------
    def paint(self, p, *args):
        p.drawPicture(0, 0, self._picture)

    # ----------------------------------------------------------------------
    def boundingRect(self):
        return QtCore.QRectF(self._picture.boundingRect())

# ----------------------------------------------------------------------
class LineSegmentItem(pg.GraphicsObject):

    def __init__(self, mode, cross_size=1., circle=0):
        pg.GraphicsObject.__init__(self)
        self._mode = mode
        self._picture = QtGui.QPicture()

        self._scaled_circle_size = 0

        self._line1_end1 = QtCore.QPoint(0, 0)
        self._line1_end2 = QtCore.QPoint(0, 0)
        self._line2_end1 = QtCore.QPoint(0, 0)
        self._line2_end2 = QtCore.QPoint(0, 0)

        self._draw_lines = False
        self._draw_point1 = False
        self._draw_point2 = False

        self._cross_size = cross_size/2
        self._circle_size = circle

        self.generate_picture()

    # ----------------------------------------------------------------------
    def set_pos(self, *argin):
        if self._mode == 'cross':
            # here we get argin[0] - center position
            # here we get argin[1] - line length

            self._line1_end1 = QtCore.QPoint(int(argin[0][0] - argin[1][0]/2), int(argin[0][1]))
            self._line1_end2 = QtCore.QPoint(int(argin[0][0] + argin[1][0]/2), int(argin[0][1]))

            self._line2_end1 = QtCore.QPoint(int(argin[0][0]), int(argin[0][1] - argin[1][1]/2))
            self._line2_end2 = QtCore.QPoint(int(argin[0][0]), int(argin[0][1] + argin[1][1]/2))

            self._draw_lines = True
            self._draw_point1 = False
            self._draw_point2 = False

        else:
            self._draw_lines = True
            self._draw_point1 = False
            self._draw_point2 = False

            if argin[0][0] is not None:
                self._line1_end1 = argin[0][0]
                self._draw_point1 = True
            else:
                self._draw_lines = False

            if argin[0][1] is not None:
                self._line1_end2 = argin[0][1]
                self._draw_point2 = True
            else:
                self._draw_lines = False

            if self._draw_lines:
                center = ((self._line1_end1.x() + self._line1_end2.x()) / 2,
                          (self._line1_end1.y() + self._line1_end2.y()) / 2)

                point = (self._line1_end1.x() * (0.5 + self._cross_size) + self._line1_end2.x() * (0.5 - self._cross_size),
                         self._line1_end1.y() * (0.5 + self._cross_size) + self._line1_end2.y() * (0.5 - self._cross_size))

                p1 = rotate(center, point, 1.57)
                p2 = rotate(center, point, -1.57)

                self._line2_end1 = QtCore.QPoint(p1[0], p1[1])
                self._line2_end2 = QtCore.QPoint(p2[0], p2[1])

        self.generate_picture()

    # ----------------------------------------------------------------------
    def new_scale(self, w, h):
        self._scaled_circle_size = int(self._circle_size*min(w, h))
        self.generate_picture()

    # ----------------------------------------------------------------------
    def generate_picture(self):

        p = QtGui.QPainter(self._picture)
        p.setPen(pg.mkPen('r', width=2, style=QtCore.Qt.DotLine))

        if self._draw_lines:
            # Horizontal
            p.drawLine(self._line1_end1, self._line1_end2)

            # Vertical
            p.drawLine(self._line2_end1, self._line2_end2)

        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(pg.mkBrush('r'))

        if self._draw_point1:
            p.drawEllipse(self._line1_end1, self._scaled_circle_size, self._scaled_circle_size)

        if self._draw_point2:
            p.drawEllipse(self._line1_end2, self._scaled_circle_size, self._scaled_circle_size)

        p.end()

    # ----------------------------------------------------------------------
    def paint(self, p, *args):
        p.drawPicture(0, 0, self._picture)

    # ----------------------------------------------------------------------
    def boundingRect(self):
        return QtCore.QRectF(self._picture.boundingRect())
