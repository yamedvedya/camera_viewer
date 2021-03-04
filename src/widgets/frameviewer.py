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
# from skimage.feature import peak_local_max
from src.utils.errors import report_error

from PyQt5 import QtCore, QtWidgets, QtGui, QtPrintSupport
from src.utils.functions import rotate

import pyqtgraph as pg
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients

from src.ui_vimbacam.FrameViewer_ui import Ui_FrameViewer

# ----------------------------------------------------------------------
class FrameViewer(QtWidgets.QWidget):
    """
    """
    status_changed = QtCore.pyqtSignal(float)
    cursor_moved = QtCore.pyqtSignal(float, float)
    range_changed = QtCore.pyqtSignal(float, float, float, float)
    refresh_numbers = QtCore.pyqtSignal()

    DEFAULT_IMAGE_EXT = "png"
    FILE_STAMP = "%Y%m%d_%H%M%S"
    DATETIME = "%Y-%m-%d %H:%M:%S"

    LABEL_BRUSH = (30, 144, 255, 170)
    LABEL_COLOR = (255, 255, 255)

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

        self._ui = Ui_FrameViewer()
        self._ui.setupUi(self)

        self._init_ui()

        self._peak_markers = PeakMarker()
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

        self._marker_widgets = []
        self._rois_widgets = []

        self._center_search_item = LineSegmentItem('center', float(self._settings.option("center_search", "cross")),
                                                    float(self._settings.option("center_search", "circle")))
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

        # a few info labels
        self._deviceLabel = self._add_label('', self._settings.node("camera_viewer/title_label"), visible=True)
        self._datetimeLabel = self._add_label("Time", self._settings.node("camera_viewer/datetime_label"), visible=True)
        self._load_label = self._add_label("Load image", self._settings.node("camera_viewer/datetime_label"), visible=False)

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
    def set_camera_device(self, camera_device):
        self._camera_device = camera_device

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
        for ind, marker in enumerate(self._camera_device.markers):
            self._marker_widgets.append(ImageMarker(marker['x'], marker['y'], self._ui.imageView))

        self._camera_device.markers_changed = False

    # ----------------------------------------------------------------------
    def update_marker(self):
        for widget, marker in zip(self._marker_widgets, self._camera_device.markers):
            widget.setPos(marker['x'], marker['y'])
            widget.setVisible(marker['visible'])

        self._camera_device.markers_need_update = False

    # ----------------------------------------------------------------------
    def rois_changed(self):
        for widget, marker, label in self._rois_widgets:
            self._ui.imageView.view.removeItem(widget)
            self._ui.imageView.view.removeItem(marker)
            self._ui.imageView.view.removeItem(label)

        self._rois_widgets = []
        for ind, values in enumerate(self._camera_device.rois):
            widget = pg.RectROI([values['x'], values['y']], [values['w'], values['h']], pen=(0, 9))
            widget.sigRegionChanged.connect(lambda rect, id=ind: self._roi_changed(rect, id))
            if values['visible']:
                widget.hide()
            else:
                widget.show()

            marker_item = LineSegmentItem('cross')
            marker_item.setVisible(values['visible'])
            self._ui.imageView.view.addItem(marker_item, ignoreBounds=True)

            self._ui.imageView.view.addItem(widget, ignoreBounds=True)
            self._rois_widgets.append([widget, marker_item,
                                       self._add_label("ROI_{}".format(ind+1),
                                                       self._settings.node("camera_viewer/roi_label"),
                                                       visible=values['visible'])])

        self._camera_device.roi_changed = False

    # ----------------------------------------------------------------------
    def update_roi(self):
        """ROI coords changed elsewhere.
        """
        for ind, (roi, cross, label) in enumerate(self._rois_widgets):

            roi.blockSignals(True)

            roi.setVisible(self._camera_device.rois[ind]['visible'])
            label.setVisible(self._camera_device.rois[ind]['visible'])

            roi.setPos([self._camera_device.rois[ind]['x'], self._camera_device.rois[ind]['y']])
            roi.setSize([self._camera_device.rois[ind]['w'], self._camera_device.rois[ind]['h']])

            label.setPos(self._camera_device.rois[ind]['x'] + self._camera_device.rois[ind]['w'],
                         self._camera_device.rois[ind]['y'] + self._camera_device.rois[ind]['h'])

            if not self._camera_device.rois[ind]['visible']:
                cross.setVisible(False)
            else:
                self._calculate_statistics()
            roi.blockSignals(False)

        self._camera_device.roi_need_update = False

    # ----------------------------------------------------------------------
    def _roi_changed(self, rect, ind):
        """Called when ROI emits sigRegionChanged signal.
        """
        if self._last_frame is not None:
            pos, size = rect.pos(), rect.size()
            max_w, max_h = self._last_frame.shape

            self._camera_device.set_roi_value(ind, 'x', max(pos.x(), 0))
            self._camera_device.set_roi_value(ind, 'y', max(pos.y(), 0))
            self._camera_device.set_roi_value(ind, 'w', min(size.x(), max_w))
            self._camera_device.set_roi_value(ind, 'h', min(size.y(), max_h))

            self._rois_widgets[ind][2].setPos(pos.x() + size.x(), pos.y() + size.y())

            self._calculate_statistics()

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
            self._calculate_statistics()

    # ----------------------------------------------------------------------
    def _find_peaks(self):
        if self._camera_device.peak_search['search']:
            try:
                if self._camera_device.peak_search['search_mode']:
                    coordinates = peak_local_max(self._last_frame,
                                                 threshold_rel=self._camera_device.peak_search['rel_threshold']/100)
                else:
                    coordinates = peak_local_max(self._last_frame,
                                                 threshold_abs=self._camera_device.peak_search['abs_threshold'])

                if len(coordinates) > 100:
                    report_error('Too many ({}) peaks found. Show first 100. Adjust the threshold'.format(len(coordinates)),
                                 self.log, self, True)
                    coordinates = coordinates[:100]
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
    def refresh_image(self):
        if self._camera_device.roi_changed:
            self.rois_changed()

        if self._camera_device.roi_need_update:
            self.update_roi()

        if self._camera_device.markers_changed:
            self.markers_changed()

        if self._camera_device.markers_need_update:
            self.update_marker()

        if self._camera_device.image_need_repaint:
            if str(self._camera_device.levels['color_map']) != '':
                colormap = self._camera_device.levels['color_map']
            else:
                colormap = 'grey'

            self._ui.imageView.imageItem.setLookupTable(
                pg.ColorMap(*zip(*Gradients[colormap.lower()]["ticks"])).getLookupTable())

            self.refresh_view()

        if self._camera_device.image_need_refresh:
            self._need_to_refresh_image = True
            self.refresh_view()

        if self._camera_device.peak_search_need_update:
            self._camera_device.peak_search_need_update = False
            self.refresh_view()

    # ----------------------------------------------------------------------
    def refresh_view(self):
        """
        """
        if hasattr(self, "_load_label"):
            self._load_label.setVisible(True)

        try:
            self._last_frame = self._camera_device.get_frame()

            picture_size = self._camera_device.get_picture_clip()
            reduction = self._camera_device.get_reduction()
            set_kwargs = {'pos': (picture_size[0], picture_size[1]),
                          'scale': (reduction, reduction)}

            if self._camera_device.levels['auto_levels']:
                set_kwargs['autoRange'] = True
                update_kwargs = {'autoLevels': True}
            else:
                set_kwargs['levels'] = (self._camera_device.levels['level_min'], self._camera_device.levels['level_max'])
                update_kwargs = {'levels': (self._camera_device.levels['level_min'], self._camera_device.levels['level_max'])}

            if self._need_to_refresh_image:
                self._ui.imageView.setImage(self._last_frame, **set_kwargs)
                self._need_to_refresh_image = False
                self._camera_device.image_need_refresh = False
            else:
                self._ui.imageView.imageItem.updateImage(self._last_frame, **update_kwargs)
                self._camera_device.image_need_repaint = False

            self._peak_markers.new_scale(self._viewRect.width(), self._viewRect.height())
            self._center_search_item.new_scale(self._viewRect.width(), self._viewRect.height())

            self._show_labels()
            self._calculate_statistics()
            self._find_peaks()

            self._redraw_projections()

            self.update_camera_label()

            self._n_frames += 1
            if time.time() - self._acq_started > 1:
                self.status_changed.emit(self._n_frames)
                self._n_frames = 0
                self._acq_started = time.time()

            if self._camera_device.levels['auto_levels']:
                self._camera_device.level_setting_change('level_min', int(self._ui.imageView.levelMin))
                self._camera_device.level_setting_change('level_max', int(self._ui.imageView.levelMax))

        except Exception as err:
            print('Error during refresh view: {}'.format(err))

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
    def _calculate_statistics(self):
        """
        """
        if self._last_frame is None:
            return

        for roi_widgets, info, data in zip(self._rois_widgets, self._camera_device.rois, self._camera_device.rois_data):
            if info['visible']:
                pos, size = roi_widgets[0].pos(), roi_widgets[0].size()

                image_size = self._camera_device.get_picture_clip()
                _image_x_pos, _image_y_pos = image_size[0], image_size[1]
                x, y, w, h = int(pos.x() - _image_x_pos), int(pos.y() - _image_y_pos), int(size.x()), int(size.y())

                array = self._last_frame[x:x + w, y:y + h]
                if array != []:
                    array[array < info['bg']] = 0  # All low values set to 0

                    roi_sum = np.sum(array)

                    try:
                        roiExtrema = scipymeasure.extrema(array)  # all in one!
                    except:
                        roiExtrema = (0, 0, (0, 0), (0, 0))

                    roi_max = (int(roiExtrema[3][0] + x + _image_x_pos), int(roiExtrema[3][1] + y + _image_y_pos))
                    roi_min = (int(roiExtrema[2][0] + x + _image_x_pos), int(roiExtrema[2][1] + y + _image_y_pos))

                    try:
                        roi_com = scipymeasure.center_of_mass(array)
                    except:
                        roi_com = (0, 0)

                    if math.isnan(roi_com[0]) or math.isnan(roi_com[1]):
                        roi_com = (0, 0)

                    roi_com = (int(roi_com[0] + x + _image_x_pos), int(roi_com[1] + y + _image_y_pos))

                    try:
                        intensity_at_com = self._last_frame[int(round(roi_com[0])), int(round(roi_com[1]))]
                    except:
                        intensity_at_com = [0, 0]

                    roi_FWHM = (self.FWHM(np.sum(array, axis=1)), self.FWHM(np.sum(array, axis=0)))

                    if info['mark'] == 'max':
                        roi_widgets[1].set_pos(roi_max, roi_FWHM)
                        roi_widgets[1].setVisible(True)
                    elif info['mark'] == 'min':
                        roi_widgets[1].set_pos(roi_min, roi_FWHM)
                        roi_widgets[1].setVisible(True)
                    elif info['mark'] == 'com':
                        roi_widgets[1].set_pos(roi_com, roi_FWHM)
                        roi_widgets[1].setVisible(True)
                    else:
                        roi_widgets[1].setVisible(False)

                    data['max_x'], data['max_y'] = roi_max
                    data['max_v'] = np.round(roiExtrema[1], 3)

                    data['min_x'], data['min_y'] = roi_min
                    data['min_v'] = np.round(roiExtrema[0], 3)

                    data['com_x'], data['com_y'] = roi_com
                    data['com_v'] = np.round(intensity_at_com, 3)

                    data['fwhm_x'], data['fwhm_y'] = roi_FWHM
                    data['sum'] = np.round(roi_sum, 3)

        self.refresh_numbers.emit()
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
    def color_map_changed(self, selected_map):

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

    def __init__(self, mode, cross_size=1., circle=0.):
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
