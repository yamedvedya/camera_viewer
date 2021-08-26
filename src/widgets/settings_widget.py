# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""

try:
    import PyTango
except ImportError:
    pass

from PyQt5 import QtCore, QtWidgets
from distutils.util import strtobool
import subprocess

import pyqtgraph as pg

from src.utils.errors import report_error
from src.widgets.base_widget import BaseWidget, APP_NAME
from src.gui.SettingsWidget_ui import Ui_SettingsWidget

from src.utils.functions import refresh_combo_box

WIDGET_NAME = 'SettingsWidget'

# ----------------------------------------------------------------------
class SettingsWidget(BaseWidget):
    """
    """
    refresh_image = QtCore.pyqtSignal()

    PARAMS_EDITOR = "atkpanel"
    SYNC_TICK = 1000  # [ms]

    # ----------------------------------------------------------------------
    def __init__(self, parent):
        """
        """
        super(SettingsWidget, self).__init__(parent)

        self._ui = Ui_SettingsWidget()
        self._ui.setupUi(self)

        self.hist = pg.HistogramLUTWidget(self, orientation='horizontal')
        self.hist.setBackground('w')
        self._ui.vl_levels.addWidget(self.hist, 1)

        self.hist.scene().sigMouseClicked.connect(self._hist_mouse_clicked)
        self.hist.item.sigLevelsChanged.connect(self._switch_off_auto_levels)
        self.hist.item.sigLookupTableChanged.connect(self.new_color_map)
        self.hist.items()[-1].setMenuEnabled(False) # TODO better way

        self._tangoMutex = QtCore.QMutex()
        self._load_camera_settings()

        self._ui.gb_screen_motor.setVisible(self._camera_device.has_motor())

        self._ui.tbAllParams.clicked.connect(self._edit_all_params)

        for ui in ['exposure', 'gain', 'FPS', 'reduce']:
            getattr(self._ui, 'sb_{}'.format(ui)).editingFinished.connect(lambda x=ui: self._settings_changed(x))

        for ui in ['view_x', 'view_y', 'view_w', 'view_h']:
            getattr(self._ui, 'sb_{}'.format(ui)).editingFinished.connect(self._change_picture_size)

        self._ui.chk_auto_levels.stateChanged.connect(lambda state:
                                                      self.level_settings_changed('auto_levels', state == 2))
        self._ui.sb_max_level.valueChanged.connect(lambda value: self.level_settings_changed('level_max', value))
        self._ui.sb_min_level.valueChanged.connect(lambda value: self.level_settings_changed('level_min', value))
        self._ui.bg_level.buttonToggled.connect((lambda button: self._new_level_mode(button)))

        self._ui.cmb_path.currentTextChanged.connect(lambda text: self._camera_device.save_settings('Path', text))
        self._ui.cmb_source.currentTextChanged.connect(lambda text: self._camera_device.save_settings('Source', text))

        self._ui.but_in_out.clicked.connect(lambda: self._camera_device.move_motor())
        self._ui.chk_auto_screen.clicked.connect(lambda state: self._camera_device.set_auto_screen(state))

        self._ui.chk_dark_image.clicked.connect(lambda state: self._camera_device.toggle_dark_image(state==2))
        self._ui.but_acq_dark_image.clicked.connect(lambda: self._camera_device.set_dark_image())
        self._ui.but_save_dark_image.clicked.connect(self._save_dark_image)
        self._ui.but_load_dark_image.clicked.connect(self._load_dark_image)

        self._ui.chk_additional_settings.clicked.connect(lambda state: self._ui.gb_ext_settings.setVisible(state))

        self._ui.chk_background.clicked.connect(lambda state: self._camera_device.save_settings('background', state))
        self._ui.dsb_sigmas.valueChanged.connect(lambda value: self._camera_device.save_settings('background_sigmas', value))

    # ----------------------------------------------------------------------
    def block_hist_signals(self, flag):
        if flag:
            self.hist.item.sigLevelsChanged.disconnect()
            self.hist.item.sigLookupTableChanged.disconnect()
        else:
            self.hist.item.sigLevelsChanged.connect(self._switch_off_auto_levels)
            self.hist.item.sigLookupTableChanged.connect(self.new_color_map)

    # ----------------------------------------------------------------------
    def _switch_off_auto_levels(self):
        self._ui.chk_auto_levels.setChecked(False)
        self.level_settings_changed('auto_levels', False)

    # ----------------------------------------------------------------------
    def _hist_mouse_clicked(self, event):
        if event.double():
            self._ui.chk_auto_levels.setChecked(True)
            self.level_settings_changed('auto_levels', True)
            self.hist.item.autoHistogramRange()

    # ----------------------------------------------------------------------
    def set_frame_to_hist(self, frame_view):
        self.hist.item.setImageItem(frame_view)

    # ----------------------------------------------------------------------
    def refresh_view(self):

        self._block_signals(True)
        self.block_hist_signals(True)
        self._ui.chk_auto_levels.setChecked(self._camera_device.levels['auto_levels'])
        self._ui.sb_min_level.setEnabled(not self._camera_device.levels['auto_levels'])
        self._ui.sb_max_level.setEnabled(not self._camera_device.levels['auto_levels'])

        if not self._ui.sb_min_level.hasFocus():
            self._ui.sb_min_level.setValue(self._camera_device.levels['levels'][0])
        if not self._ui.sb_max_level.hasFocus():
            self._ui.sb_max_level.setValue(self._camera_device.levels['levels'][1])

        self.hist.item.restoreState(self._camera_device.levels)

        self._ui.rb_lin_level.setChecked(self._camera_device.level_mode == 'lin')
        self._ui.rb_log_level.setChecked(self._camera_device.level_mode == 'log')
        self._ui.rb_sqrt_level.setChecked(self._camera_device.level_mode == 'sqrt')

        self._ui.sb_reduce.setValue(self._camera_device.get_reduction())
        self._ui.chk_auto_screen.setChecked(self._camera_device.auto_screen)

        self._ui.but_save_dark_image.setEnabled(self._camera_device.has_dark_image())
        self._ui.chk_dark_image.setEnabled(self._camera_device.has_dark_image())
        self._ui.but_acq_dark_image.setEnabled(self._camera_device.got_first_frame)

        self._ui.chk_dark_image.setChecked(self._camera_device.subtract_dark_image)

        self._block_signals(False)
        self.block_hist_signals(False)

    # ----------------------------------------------------------------------
    def new_color_map(self, lut_item):
        lut = lut_item.saveState()
        lut['auto_levels'] = self._ui.chk_auto_levels.isChecked()

        self._camera_device.level_setting_change(lut)
        self.refresh_image.emit()

    # ----------------------------------------------------------------------
    def level_settings_changed(self, param, value):
        lev = self.hist.item.getLevels()
        if param == 'level_max':
            lev[1] = float(value)
        elif param == 'level_min':
            lev[0] = float(value)

        self.hist.item.setLevels(lev[0], lev[1])
        self.new_color_map(self.hist.item)

    # ----------------------------------------------------------------------
    def _load_camera_settings(self):

        result = True
        try:
            for layout in ['exposure', 'folder', 'FPS', 'source', 'background']:
                getattr(self._ui, 'frame_{}'.format(layout)).setVisible(layout in self._camera_device.visible_layouts())

            with QtCore.QMutexLocker(self._tangoMutex):

                self.refresh_view()
                self._sync_settings()

                self._ui.cmb_path.clear()
                possible_folders = self._camera_device.get_settings('possible_folders', str)
                if possible_folders != '':
                    self._ui.cmb_path.setEnabled(True)
                    self._ui.cmb_path.addItems(possible_folders)
                    refresh_combo_box(self._ui.cmb_path, self._camera_device.get_settings('path', str))
                else:
                    self._ui.cmb_path.setEnabled(False)

                self._ui.cmb_source.clear()
                possible_sources = self._camera_device.get_settings('possible_sources', str)
                if possible_sources != '':
                    self._ui.cmb_source.setEnabled(True)
                    self._ui.cmb_source.addItems(possible_sources)
                    refresh_combo_box(self._ui.cmb_source, self._camera_device.get_settings('source', str))
                else:
                    self._ui.cmb_source.setEnabled(False)

        except Exception as err:
            report_error(err, self._log, self)
            result = False

        finally:
            self._block_signals(False)
            return result

    # ----------------------------------------------------------------------
    def _sync_settings(self):

        motor_position = self._camera_device.motor_position()
        if motor_position is not None:
            self._ui.but_in_out.setText('Move Out' if motor_position else 'Move In')
            self._ui.lb_screen_status.setText('Screen is In' if motor_position else 'Screen is Out')

        if not self._ui.sb_exposure.hasFocus():
            exposure_time = self._camera_device.get_settings('exposure', int)
            self._ui.sb_exposure.setValue(exposure_time)

        if not self._ui.sb_gain.hasFocus():
            gain_value = self._camera_device.get_settings('gain', int)
            self._ui.sb_gain.setValue(gain_value)

        for ui in ['view_x', 'view_y']:
            if not getattr(self._ui, 'sb_{}'.format(ui)).hasFocus():
                getattr(self._ui, 'sb_{}'.format(ui)).setMaximum(1e6)
                getattr(self._ui, 'sb_{}'.format(ui)).setValue(self._camera_device.get_settings(ui, int))

        for ui in ['view_w', 'view_h']:
            if not getattr(self._ui, 'sb_{}'.format(ui)).hasFocus():
                getattr(self._ui, 'sb_{}'.format(ui)).setMaximum(1e6)
                value = self._camera_device.get_settings(ui, int)
                if value == 0:
                    value = 1
                getattr(self._ui, 'sb_{}'.format(ui)).setValue(value)

        self._update_picture_size_limits()

        if not self._ui.sb_FPS.hasFocus():
            fps = self._camera_device.get_settings('FPS', int)
            fps_max = self._camera_device.get_settings('FPSmax', int)
            if fps == 0:
                fps = 25
            if fps_max == 0:
                fps_max = 100

            self._ui.sb_FPS.setMaximum(fps_max)
            self._ui.sb_FPS.setValue(fps)

        if not self._ui.chk_background.hasFocus():
            self._ui.chk_background.setChecked(self._camera_device.get_settings('background', bool))

        if not self._ui.dsb_sigmas.hasFocus():
            self._ui.dsb_sigmas.setValue(self._camera_device.get_settings('background_sigmas', float))

    # ----------------------------------------------------------------------
    def _save_dark_image(self):
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save dark image",
                                                            self._settings.option("save_folder", "default"),
                                                            "Numpy files (*.npy)")
        if fileName:
            self._camera_device.save_dark_image(fileName)

    # ----------------------------------------------------------------------
    def _load_dark_image(self):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load dark image",
                                                             self._settings.option("save_folder", "default"),
                                                             "Numpy files (*.npy)")
        if file_name:
            self._camera_device.load_dark_image(file_name)

    # ----------------------------------------------------------------------
    def _update_picture_size_limits(self):

        max_w, max_h = self._camera_device.get_max_picture_size()
        view_x = min(max(self._ui.sb_view_x.value(), 0), max_w)
        view_y = min(max(self._ui.sb_view_y.value(), 0), max_h)

        view_w = min(self._ui.sb_view_w.value(), max_w)
        if view_w == 0:
            view_w = 1
            self._ui.sb_view_w.blockSignals(True)
            self._ui.sb_view_w.setValue(view_w)
            self._ui.sb_view_w.blockSignals(False)

        view_h = min(self._ui.sb_view_h.value(), max_h)
        if view_h == 0:
            view_h = 1
            self._ui.sb_view_h.blockSignals(True)
            self._ui.sb_view_h.setValue(view_h)
            self._ui.sb_view_h.blockSignals(False)

        self._ui.sb_view_x.setMaximum(max_w - view_w)
        self._ui.sb_view_y.setMaximum(max_h - view_h)
        self._ui.sb_view_w.setMaximum(max_w - view_x)
        self._ui.sb_view_h.setMaximum(max_h - view_y)

        return view_x, view_y, view_w, view_h

    # ----------------------------------------------------------------------
    def _change_picture_size(self):

        self._camera_device.set_picture_clip(self._update_picture_size_limits())
        self.refresh_image.emit()

    # ----------------------------------------------------------------------
    def _new_level_mode(self, button):

        self._camera_device.set_new_level_mode(str(button.text()).lower())

    # ----------------------------------------------------------------------
    def _marker_changed(self, num, coor, value):
        """
        """
        self._markers[num][str(coor)] = value
        self._camera_device.save_settings('marker_{:d}_{}'.format(num, str(coor)), value)
        self.marker_changed.emit(num)

    # ----------------------------------------------------------------------
    def _settings_changed(self, name):
        """
        """
        if name == 'reduce':
            self._camera_device.set_reduction(self._ui.sb_reduce.value())
            self.refresh_image.emit()

        self._camera_device.save_settings(name, getattr(self._ui, 'sb_{}'.format(name)).value())

    # ----------------------------------------------------------------------
    def _edit_all_params(self):
        """
        """
        server = self._tangoServer
        server = "/" + "/".join(server.split("/")[1:])

        self._log.info("Edit all params, server: {}".format(server))

        subprocess.Popen([self.PARAMS_EDITOR, server])

    # ----------------------------------------------------------------------
    def load_ui_settings(self, camera_name):
        super(SettingsWidget, self).load_ui_settings(camera_name)

        settings = QtCore.QSettings(APP_NAME)

        state = False
        try:
            state = strtobool(settings.value(f"{WIDGET_NAME}_{camera_name}/AdditionalSettings"))
        except:
            pass

        self._ui.gb_ext_settings.setVisible(state)
        self._ui.chk_additional_settings.setChecked(state)

    # ----------------------------------------------------------------------
    def save_ui_settings(self, camera_name):
        super(SettingsWidget, self).save_ui_settings(camera_name)

        settings = QtCore.QSettings(APP_NAME)
        settings.setValue(f"{WIDGET_NAME}_{camera_name}/AdditionalSettings", self._ui.chk_additional_settings.isChecked())

    # ----------------------------------------------------------------------
    def _block_signals(self, flag):
        """
        """
        self._ui.sb_exposure.blockSignals(flag)
        self._ui.sb_gain.blockSignals(flag)

        self._ui.cmb_path.blockSignals(flag)

        self._ui.rb_lin_level.blockSignals(flag)
        self._ui.rb_log_level.blockSignals(flag)
        self._ui.rb_sqrt_level.blockSignals(flag)