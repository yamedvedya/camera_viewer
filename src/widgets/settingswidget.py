# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""

import logging
import subprocess

try:
    import PyTango
except ImportError:
    pass

from src.utils.errors import report_error
from PyQt5 import QtCore, QtWidgets

from src.ui_vimbacam.SettingsWidget_ui import Ui_SettingsWidget
from src.widgets.marker import Marker

from src.utils.functions import refresh_combo_box

# ----------------------------------------------------------------------
class SettingsWidget(QtWidgets.QWidget):
    """
    """
    marker_changed = QtCore.pyqtSignal(int)
    markers_changed = QtCore.pyqtSignal()
    roi_changed = QtCore.pyqtSignal(int)
    roi_marker_selected = QtCore.pyqtSignal(str)

    color_map_changed = QtCore.pyqtSignal(str)
    levels_changed = QtCore.pyqtSignal(float, float)
    enable_auto_levels = QtCore.pyqtSignal(bool)
    set_dark_image = QtCore.pyqtSignal()
    remove_dark_image = QtCore.pyqtSignal()
    image_size_changed = QtCore.pyqtSignal(float, float, float, float)
    reset_center_search = QtCore.pyqtSignal(list)
    new_image_reduction = QtCore.pyqtSignal(int)

    PARAMS_EDITOR = "atkpanel"
    SYNC_TICK = 1000  # [ms]
    NUM_MARKERS = 2

    # ----------------------------------------------------------------------
    def __init__(self, settings, parent):
        """
        """
        super(SettingsWidget, self).__init__(parent)
        self.settings = settings
        self.log = logging.getLogger("cam_logger")

        self._ui = Ui_SettingsWidget()
        self._ui.setupUi(self)
        self._marker_grid = QtWidgets.QGridLayout(self._ui.layout_markers)
        self._markers_widgets = []

        self._camera_device = None
        self._rois, self._markers, self._statistics = None, None, None
        self._current_roi_index = None

        self._statistics_marker = 'none'

        self._first_camera = True

        self._picture_width = None
        self._picture_height = None

        self._ui.tbAllParams.clicked.connect(self._edit_all_params)
        for ui in ['ExposureTime', 'Gain', 'FPS', 'Reduce']:
            getattr(self._ui, 'sb{}'.format(ui)).editingFinished.connect(lambda x=ui: self._settings_changed(x))

        for ui in ['ViewX', 'ViewY', 'ViewW', 'ViewH']:
            getattr(self._ui, 'sb{}'.format(ui)).editingFinished.connect(lambda x=ui: self._range_changed(x))

        self._ui.chkAutoLevels.stateChanged.connect(self._autoLevelsChanged)
        self._ui.sbMinLevel.valueChanged.connect(self._levelsChanged)
        self._ui.sbMaxLevel.valueChanged.connect(self._levelsChanged)
        self._ui.cbColorMap.currentIndexChanged.connect(self._colorMapChanged)

        for ui in ['RoiX', 'RoiY', 'RoiWidth', 'RoiHeight', 'Threshold']:
            getattr(self._ui, 'sb{}'.format(ui)).valueChanged.connect(lambda value, name=ui: self._roi_changed(name, value))
        self._ui.chbShowRoi.stateChanged.connect(lambda: self._make_roi_visible(self._ui.chbShowRoi.isChecked()))

        self._ui.pbInOut.clicked.connect(lambda: self._camera_device.move_motor())
        self._ui.chbShowCom.stateChanged.connect(lambda: self._roi_marker_changed('com'))
        self._ui.chbShowMin.stateChanged.connect(lambda: self._roi_marker_changed('min'))
        self._ui.chbShowMax.stateChanged.connect(lambda: self._roi_marker_changed('max'))
        self._ui.tbDarkImage.clicked.connect(self.set_dark_image)
        self._ui.tbDarkImageDelete.clicked.connect(self.remove_dark_image)
        self._ui.but_add_marker.clicked.connect(self._add_marker)

        self._ui.cb_counter.currentIndexChanged.connect(lambda: self._camera_device.set_counter(
            self._ui.cb_counter.currentText()))

        self._tangoMutex = QtCore.QMutex()

        #keep in sync with TANGO
        self._syncTimer = QtCore.QTimer(self)
        self._syncTimer.timeout.connect(self._sync_settings)
        self._syncTimer.start(self.SYNC_TICK)

    # ----------------------------------------------------------------------
    def close(self):
        self._syncTimer.stop()
        super(SettingsWidget, self).close()

    # ----------------------------------------------------------------------
    def _sync_settings(self):
        motor_position = self._camera_device.motor_position()
        if motor_position is not None:
            self._ui.pbInOut.setText('Move Out' if motor_position else 'Move In')
            self._ui.lb_screen_status.setText('Screen is In' if motor_position else 'Screen is Out')

        counter_name = self._camera_device.get_counter()
        if counter_name is not None:
            refresh_combo_box(self._ui.cb_counter, counter_name)

    # ----------------------------------------------------------------------
    def set_variables(self, camera_device, rois, markers, statistics, current_roi_index):
        self._camera_device = camera_device
        self._rois = rois
        self._markers = markers
        self._statistics = statistics
        self._current_roi_index = current_roi_index

    # ----------------------------------------------------------------------
    def close_camera(self, auto_screen):
        if not self._first_camera:
            self.save_camera_settings()

        if self._ui.chk_auto_screen.isChecked() and auto_screen:
            self._camera_device.move_motor(False)

    # ----------------------------------------------------------------------
    def set_new_camera(self, auto_screen):
        if self.load_camera_settings():
            self._first_camera = False
            self._ui.gb_screen_motor.setVisible(self._camera_device.has_motor())
            self._ui.gb_sardana.setVisible(self._camera_device.has_counter())
            if self._ui.chk_auto_screen.isChecked() and auto_screen:
                self._camera_device.move_motor(True)
            return True
        else:
            return False

    # ----------------------------------------------------------------------
    def _add_marker(self):
        self._markers.append({'x': 0, 'y': 0})
        self._update_marker_layout()

    # ----------------------------------------------------------------------
    def _delete_marker(self, id):

        del self._markers[id]
        self._update_marker_layout()

    # ----------------------------------------------------------------------
    def _update_marker_layout(self, save=True):

        layout = self._ui.layout_markers.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item:
                w = layout.itemAt(i).widget()
                if w:
                    layout.removeWidget(w)
                    w.setVisible(False)

        self._markers_widgets = []
        for ind, values in enumerate(self._markers):
            widget = Marker(ind)
            widget.marker_changed.connect(self._marker_changed)
            widget.delete_me.connect(self._delete_marker)
            widget.set_values(values)
            widget.setVisible(True)
            layout.addWidget(widget)
            self._markers_widgets.append(widget)

        self.markers_changed.emit()
        if save:
            self.save_camera_settings()

    # ----------------------------------------------------------------------
    def _get_picture_size(self):
        return (min(max(self._ui.sbViewX.value(), 0), self._picture_width),
                min(max(self._ui.sbViewY.value(), 0), self._picture_height),
                min(max(self._ui.sbViewW.value(), 1), self._picture_width),
                min(max(self._ui.sbViewH.value(), 1), self._picture_height))

    # ----------------------------------------------------------------------
    def _change_picture_size(self):

        view_x, view_y, view_w, view_h = self._get_picture_size()

        self._ui.sbViewX.setMaximum(self._picture_width - view_w)
        self._ui.sbViewY.setMaximum(self._picture_height - view_h)
        self._ui.sbViewW.setMaximum(self._picture_width - view_x)
        self._ui.sbViewH.setMaximum(self._picture_height - view_y)

        self.image_size_changed.emit(view_x, view_y, view_w, view_h)
        self._camera_device.change_picture_size([view_x, view_y, view_w, view_h])

    # ----------------------------------------------------------------------
    def _save_one_setting(self, name, value):
        try:
            self._camera_device.save_settings(name, value)
        except Exception as err:
            report_error(err, self.log, self)

    # ----------------------------------------------------------------------
    def update_levels(self, min, max, map):
        """
        """
        self._block_signals(True)
        self._ui.sbMinLevel.setValue(min)
        self._ui.sbMaxLevel.setValue(max)

        index = self._ui.cbColorMap.findText(map, QtCore.Qt.MatchFixedString)
        if index >= 0:
            self._ui.cbColorMap.setCurrentIndex(index)

        self.levels_changed.emit(min, max)
        self.color_map_changed.emit(str(self._ui.cbColorMap.currentText()).lower())
        self._block_signals(False)

    # ----------------------------------------------------------------------
    def update_marker(self, num):
        """
        """
        self._markers_widgets[num].set_values(self._markers[num])
        self._camera_device.save_settings('marker_{:d}_x'.format(num), self._markers[num]['x'])
        self._camera_device.save_settings('marker_{:d}_y'.format(num), self._markers[num]['y'])

    # ----------------------------------------------------------------------
    def update_roi(self, index):
        """
        """
        self._block_signals(True)
        for ui in ["RoiX", "RoiY", "RoiWidth", "RoiHeight"]:
            getattr(self._ui, 'sb{}'.format(ui)).setValue(self._rois[index][ui])
            self._camera_device.save_settings(ui, self._rois[index][ui])
        self._block_signals(False)

    # CS
    # ----------------------------------------------------------------------
    def update_roi_statistics(self, roi_index):

        """Stats changed     """

        try:
            self._ui.leMaxVal.setText('{:2.2f}'.format(self._statistics[roi_index]["extrema"][1]))
        except:
            self._ui.leMaxVal.setText('')

        try:
            self._ui.leMinVal.setText('{:2.2f}'.format(self._statistics[roi_index]["extrema"][0]))
        except:
            self._ui.leMinVal.setText('')

        try:
            self._ui.leMinX.setText(str(self._statistics[roi_index]["extrema"][2][0]))
        except:
            self._ui.leMinX.setText('')

        try:
            self._ui.leMinY.setText(str(self._statistics[roi_index]["extrema"][2][1]))
        except:
            self._ui.leMinY.setText('')

        try:
            self._ui.leMaxX.setText(str(self._statistics[roi_index]["extrema"][3][0]))
        except:
            self._ui.leMaxX.setText('')

        try:
            self._ui.leMaxY.setText(str(self._statistics[roi_index]["extrema"][3][1]))
        except:
            self._ui.leMaxY.setText('')

        try:
            self._ui.leComX.setText(str("{:10.2f}".format(self._statistics[roi_index]["com_pos"][0])))
        except:
            self._ui.leComX.setText('')

        try:
            self._ui.leComY.setText(str("{:10.2f}".format(self._statistics[roi_index]["com_pos"][1])))
        except:
            self._ui.leComY.setText('')

        try:
            self._ui.leComVal.setText(str(self._statistics[roi_index]["intensity_at_com"]))
        except:
            self._ui.leComVal.setText('')

        try:
            self._ui.leFwhmX.setText(str(self._statistics[roi_index]["fwhm"][0]))
        except:
            self._ui.leFwhmX.setText('')

        try:
            self._ui.leFwhmY.setText(str(self._statistics[roi_index]["fwhm"][1]))
        except:
            self._ui.leFwhmY.setText('')

        try:
            self._ui.leSum.setText(str(self._statistics[roi_index]["sum"]))
        except:
            self._ui.leSum.setText('')

    # ----------------------------------------------------------------------
    def _marker_changed(self, num, coor, value):
        """
        """
        self._markers[num][str(coor)] = value
        self._camera_device.save_settings('marker_{:d}_{}'.format(num, str(coor)), value)
        self.marker_changed.emit(num)

    # ----------------------------------------------------------------------
    def _roi_marker_changed(self, button):
        """
        """

        if button == 'max':
            if self._statistics_marker == 'max':
                self._statistics_marker = 'none'
            else:
                self._statistics_marker = 'max'
        elif button == 'min':
            if self._statistics_marker == 'min':
                self._statistics_marker = 'none'
            else:
                self._statistics_marker = 'min'
        elif button == 'com':
            if self._statistics_marker == 'com':
                self._statistics_marker = 'none'
            else:
                self._statistics_marker = 'com'

        self._block_signals(True)
        self._ui.chbShowMax.setChecked(self._statistics_marker == 'max')
        self._ui.chbShowMin.setChecked(self._statistics_marker == 'min')
        self._ui.chbShowCom.setChecked(self._statistics_marker == 'com')
        self._block_signals(False)

        self.roi_marker_selected.emit(self._statistics_marker)

    # ----------------------------------------------------------------------
    def _roi_changed(self, name, value):
        """
        """
        self._rois[self._current_roi_index[0]][name] = value
        self._camera_device.save_settings(name, self._rois[self._current_roi_index[0]][name])
        self.roi_changed.emit(self._current_roi_index[0])

    # ----------------------------------------------------------------------
    def _make_roi_visible(self, state):

        self._rois[self._current_roi_index[0]]['Roi_Visible'] = state
        self._camera_device.save_settings('Roi_Visible', state)
        self._ui.sbRoiX.setEnabled(state)
        self._ui.sbRoiY.setEnabled(state)
        self._ui.sbRoiWidth.setEnabled(state)
        self._ui.sbRoiHeight.setEnabled(state)

        self.roi_changed.emit(self._current_roi_index[0])

    # ----------------------------------------------------------------------
    def _settings_changed(self, name):
        """
        """
        if name == 'Reduce':
            self.new_image_reduction.emit(int(getattr(self._ui, 'sb{}'.format(name)).value()))

        with QtCore.QMutexLocker(self._tangoMutex):
            self._camera_device.save_settings(name, getattr(self._ui, 'sb{}'.format(name)).value())

    # ----------------------------------------------------------------------
    def _range_changed(self, name):

        with QtCore.QMutexLocker(self._tangoMutex):
            self._camera_device.save_settings(name, getattr(self._ui, 'sb{}'.format(name)).value())

        self._change_picture_size()

    # ----------------------------------------------------------------------
    def _edit_all_params(self):
        """
        """
        server = self._tangoServer
        server = "/" + "/".join(server.split("/")[1:])

        self.log.info("Edit all params, server: {}".format(server))

        subprocess.Popen([self.PARAMS_EDITOR, server])

    # ----------------------------------------------------------------------
    def save_ui_settings(self, settings):
        """
        Args:
            (QSettings)
        """

        settings.setValue("SettingsWidget/geometry", self.saveGeometry())

    # ----------------------------------------------------------------------
    def load_ui_settings(self, settings):
        """
        Args:
            (QSettings)
        """
        try:
            self.restoreGeometry(settings.value("SettingsWidget/geometry"))
        except:
            pass

    # ----------------------------------------------------------------------
    def load_camera_settings(self):

        self._block_signals(True)
        result = True

        try:
            self.update_levels(self._camera_device.get_settings('level_min', int),
                               self._camera_device.get_settings('level_max', int),
                               self._camera_device.get_settings('color_map', str))

            self._ui.chkAutoLevels.setChecked(self._camera_device.get_settings('auto_levels_set', bool))
            self._autoLevelsChanged()

            max_level_limit = self._camera_device.get_settings('max_level_limit', int)
            if max_level_limit is None:
                max_level_limit = 10000
            self._ui.sbMaxLevel.setMaximum(max_level_limit)
            self._ui.sbMinLevel.setMaximum(max_level_limit)

            reduction = max(1, self._camera_device.get_settings('Reduce', int))
            self._ui.sbReduce.setValue(reduction)
            self.new_image_reduction.emit(reduction)

            self._ui.chk_auto_screen.setChecked(self._camera_device.get_settings('auto_screen', bool))

            for roi_ui in ['RoiX', 'RoiY', 'RoiWidth', 'RoiHeight']:
                self._rois[self._current_roi_index[0]][roi_ui] = self._camera_device.get_settings(roi_ui, int)

            self._rois[self._current_roi_index[0]]['Threshold'] = self._camera_device.get_settings('Threshold', float)

            roi_visible = self._camera_device.get_settings('Roi_Visible', bool)
            self._rois[self._current_roi_index[0]]['Roi_Visible'] = roi_visible
            self.update_roi(self._current_roi_index[0])
            self._ui.chbShowRoi.setChecked(roi_visible)
            self._ui.sbRoiX.setEnabled(roi_visible)
            self._ui.sbRoiY.setEnabled(roi_visible)
            self._ui.sbRoiWidth.setEnabled(roi_visible)
            self._ui.sbRoiHeight.setEnabled(roi_visible)

            self.roi_changed.emit(self._current_roi_index[0])

            for ind in range(len(self._markers))[::-1]:
                del self._markers[ind]

            for ind in range(self._camera_device.get_settings('num_markers', int)):
                self._markers.append({'x': self._camera_device.get_settings('marker_{:d}_x'.format(ind), int),
                                      'y': self._camera_device.get_settings('marker_{:d}_y'.format(ind), int)})
            self._update_marker_layout(False)

            with QtCore.QMutexLocker(self._tangoMutex):
                self._ui.sbExposureTime.setValue(self._camera_device.get_settings('ExposureTime', int))
                self._ui.sbGain.setValue(self._camera_device.get_settings('Gain', int))

                self._picture_width = self._camera_device.get_settings('wMax', int)
                self._picture_height = self._camera_device.get_settings('hMax', int)

                viewX = self._camera_device.get_settings('viewX', int)
                viewY = self._camera_device.get_settings('viewY', int)
                viewW = self._camera_device.get_settings('viewW', int)
                viewH = self._camera_device.get_settings('viewH', int)

                self._ui.sbViewX.setMaximum(1e5)
                self._ui.sbViewY.setMaximum(1e5)
                self._ui.sbViewW.setMaximum(1e5)
                self._ui.sbViewH.setMaximum(1e5)

                if viewX is not None:
                    self._ui.sbViewX.setDisabled(False)
                    self._ui.sbViewX.setValue(viewX)
                else:
                    self._ui.sbViewX.setDisabled(True)

                if viewY is not None:
                    self._ui.sbViewY.setDisabled(False)
                    self._ui.sbViewY.setValue(viewY)
                else:
                    self._ui.sbViewY.setDisabled(True)

                if viewW is not None:
                    self._ui.sbViewW.setDisabled(False)
                    self._ui.sbViewW.setValue(viewW)
                else:
                    self._ui.sbViewW.setDisabled(True)

                if viewH is not None:
                    self._ui.sbViewH.setDisabled(False)
                    self._ui.sbViewH.setValue(viewH)
                else:
                    self._ui.sbViewH.setDisabled(True)

                self._change_picture_size()

                fps = self._camera_device.get_settings('FPS', int)
                fps_max = self._camera_device.get_settings('FPSmax', int)
                if fps is None:
                    fps = 25
                if fps_max is None:
                    fps_max = 100

                self._ui.sbFPS.setValue(fps)
                self._ui.sbFPS.setMaximum(fps_max)

                self._roi_marker_changed(self._camera_device.get_settings('Statistics_Marker', str))

        except Exception as err:
            report_error(err, self.log, self)
            result = False

        finally:
            self._block_signals(False)
            return result

    # ----------------------------------------------------------------------
    def save_camera_settings(self):

        try:
            self._camera_device.save_settings('level_min', self._ui.sbMinLevel.value())
            self._camera_device.save_settings('level_max', self._ui.sbMaxLevel.value())
            self._camera_device.save_settings('color_map', str(self._ui.cbColorMap.currentText()).lower())
            self._camera_device.save_settings('auto_levels_set', self._ui.chkAutoLevels.isChecked())
            self._camera_device.save_settings('auto_screen', self._ui.chk_auto_screen.isChecked())

            for roi_param in ['RoiX', 'RoiY', 'RoiWidth', 'RoiHeight', 'Threshold', 'Roi_Visible']:
                self._camera_device.save_settings(roi_param, self._rois[self._current_roi_index[0]][roi_param])

            self._camera_device.save_settings('num_markers', len(self._markers))
            for num, values in enumerate(self._markers):
                self._camera_device.save_settings('marker_{:d}_x'.format(num), values['x'])
                self._camera_device.save_settings('marker_{:d}_y'.format(num), values['y'])

            self._camera_device.save_settings('Statistics_Marker', self._statistics_marker)

            for ui in ['ExposureTime', 'Gain', 'FPS', 'Reduce']:
                self._camera_device.save_settings(ui, int(getattr(self._ui, 'sb{}'.format(ui)).value()))

            view_x, view_y, view_w, view_h = self._get_picture_size()

            self._camera_device.save_settings('viewX', view_x)
            self._camera_device.save_settings('viewY', view_y)
            self._camera_device.save_settings('viewW', view_w)
            self._camera_device.save_settings('viewH', view_h)

            self.log.debug("Settings saved")

        except Exception as err:
            report_error(err, self.log, self)


    # ----------------------------------------------------------------------
    def _block_signals(self, flag):
        """
        """
        self._ui.sbRoiX.blockSignals(flag)
        self._ui.sbRoiY.blockSignals(flag)
        self._ui.sbRoiWidth.blockSignals(flag)
        self._ui.sbRoiHeight.blockSignals(flag)
        self._ui.chbShowRoi.blockSignals(flag)
        self._ui.sbExposureTime.blockSignals(flag)
        self._ui.sbGain.blockSignals(flag)

        self._ui.chbShowMax.blockSignals(flag)
        self._ui.chbShowMin.blockSignals(flag)
        self._ui.chbShowCom.blockSignals(flag)
        self._ui.chbShowRoi.blockSignals(flag)

    # ----------------------------------------------------------------------
    def _autoLevelsChanged(self):

        if self._ui.chkAutoLevels.isChecked():
            self._ui.sbMinLevel.setEnabled(False)
            self._ui.sbMaxLevel.setEnabled(False)
            self.enable_auto_levels.emit(True)
        else:
            self._ui.sbMinLevel.setEnabled(True)
            self._ui.sbMaxLevel.setEnabled(True)
            self.enable_auto_levels.emit(False)
            self._levelsChanged()

    # ----------------------------------------------------------------------
    def _levelsChanged(self):

        self.levels_changed.emit(self._ui.sbMinLevel.value(), self._ui.sbMaxLevel.value())

    # ----------------------------------------------------------------------
    def _colorMapChanged(self):

        self.color_map_changed.emit(str(self._ui.cbColorMap.currentText()).lower())