# Created by matveyev at 22.02.2022

import logging
import time

from PyQt5 import QtWidgets, QtGui, QtCore

from petra_camera.utils.functions import get_save_path
from petra_camera.widgets.camera_settings import CameraSettings
from petra_camera.widgets.batch_progress import BatchProgress
from petra_camera.gui.SettingsDialog_ui import Ui_SettingsDialog
from petra_camera.utils.tango_utils import TangoDBsInfo

from petra_camera.constants import APP_NAME
logger = logging.getLogger(APP_NAME)


class ProgramSetup(QtWidgets.QDialog):

    WIDGET_NAME = 'ProgramSetup'

    camera_done = QtCore.pyqtSignal('qint64')
    rename_camera = QtCore.pyqtSignal('qint64')

    # ----------------------------------------------------------------------
    def __init__(self, main_window):
        """
        """
        super(ProgramSetup, self).__init__()
        self._ui = Ui_SettingsDialog()
        self._ui.setupUi(self)

        self._main_window = main_window

        self._settings = main_window.settings

        self.tango_dbs_info = TangoDBsInfo()

        self.cameras_to_reload = []

        self.btn_add_camera = QtWidgets.QToolButton(self)
        self.btn_add_camera.setText('Add camera') #.setIcon(QtGui.QIcon(":/icons/plus_small.png"))
        self.btn_add_camera.clicked.connect(self._add_camera)
        self._ui.tb_cameras.setCornerWidget(self.btn_add_camera, QtCore.Qt.TopRightCorner)
        self._ui.tb_cameras.cornerWidget().setMinimumSize(self.btn_add_camera.sizeHint())

        self._ui.cmd_save_folder.clicked.connect(self._new_save_folder)
        self._ui.cmd_reset_settings.clicked.connect(self._reset_settings)

        self._ui.cmd_roi_frame_color.clicked.connect(lambda: self._pick_color('cmd_roi_frame_color'))
        self._ui.cmd_roi_bkg_color.clicked.connect(lambda: self._pick_color('cmd_roi_bkg_color'))
        self._ui.cmd_marker_color.clicked.connect(lambda: self._pick_color('cmd_marker_color'))
        self._ui.cmd_title_bkg_color.clicked.connect(lambda: self._pick_color('cmd_title_bkg_color'))
        self._ui.cmd_roi_label_font_color.clicked.connect(lambda: self._pick_color('cmd_roi_label_font_color'))
        self._ui.cmd_title_font_color.clicked.connect(lambda: self._pick_color('cmd_title_font_color'))

        self._ui.cmd_roi_label_font.clicked.connect(lambda: self._pick_font('cmd_roi_label_font'))
        self._ui.cmd_title_font.clicked.connect(lambda: self._pick_font('cmd_title_font'))

        self._display_settings()

    # ----------------------------------------------------------------------
    def _reset_settings(self):

        ok = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, 'Attention!', 'Are you sure want to reset settings to default?',
                                   QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.No).exec_()
        if ok == QtWidgets.QMessageBox.Ok:
            self._main_window.reset_settings_to_default()

            QtCore.QSettings(APP_NAME).setValue("{}/geometry".format(self.WIDGET_NAME), self.saveGeometry())

            super(ProgramSetup, self).accept()

    # ----------------------------------------------------------------------
    def _new_save_folder(self):

        folder = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select safe folder', self._ui.le_save_path.text())
        if folder:
            self._ui.le_save_path.setText(folder)

    # ----------------------------------------------------------------------
    def _display_settings(self):

        self._ui.le_save_path.setText(get_save_path(self._settings))

        self._ui.cmd_roi_frame_color.setStyleSheet("QPushButton {background-color: " +
                                                   f"{self._settings.option('roi', 'fr_color')}" + ";}")

        self._ui.cmd_roi_label_font.setText(self._settings.option('roi', 'font'))
        font = self._settings.option('roi', 'font').split(',')
        self._ui.cmd_roi_label_font.setFont(QtGui.QFont(font[0], int(font[1])))

        self._ui.cmd_roi_label_font_color.setStyleSheet("QPushButton {background-color: " +
                                                   f"{self._settings.option('roi', 'fg_color')}" + ";}")

        self._ui.cmd_roi_bkg_color.setStyleSheet("QPushButton {background-color: " +
                                                 f"{self._settings.option('roi', 'bg_color')}" + ";}")

        self._ui.cmd_marker_color.setStyleSheet("QPushButton {background-color: " +
                                                f"{self._settings.option('marker', 'fr_color')}" + ";}")

        self._ui.cmd_title_font.setText(self._settings.option('title', 'font'))
        font = self._settings.option('title', 'font').split(',')
        self._ui.cmd_title_font.setFont(QtGui.QFont(font[0], int(font[1])))

        self._ui.cmd_title_font_color.setStyleSheet("QPushButton {background-color: " +
                                                    f"{self._settings.option('title', 'fg_color')}" + ";}")
        self._ui.cmd_title_bkg_color.setStyleSheet("QPushButton {background-color: " +
                                                   f"{self._settings.option('title', 'bg_color')}" + ";}")

        if self._settings.has_node('roi_server') and self._settings.option("roi_server", "enable").lower() == "true":
            self._ui.chk_roi_server_enable.setChecked(True)
            self._ui.le_roi_server_host.setEnabled(True)
            self._ui.le_roi_server_host.setText(self._settings.option("roi_server", "host"))
            self._ui.le_roi_server_port.setEnabled(True)
            self._ui.le_roi_server_port.setText(self._settings.option("roi_server", "port"))
        else:
            self._ui.chk_roi_server_enable.setChecked(False)
            self._ui.le_roi_server_host.setEnabled(False)
            self._ui.le_roi_server_host.setEnabled(False)

        self._ui.dsb_cross_size.setValue(float(self._settings.option("center_search", "cross")))
        self._ui.dsb_circle_size.setValue(float(self._settings.option("center_search", "circle")))

        self.cameras_settings = self._settings.get_nodes('camera')

        self.loader_progress = BatchProgress()
        self.loader_progress.new_cameras_set([(int(camera.get('id')), camera.get('name')) for camera in self.cameras_settings])
        self.loader_progress.set_title('Get camera settings')
        self.loader_progress.show()

        self.loader = CameraLoader(self)
        self.camera_done.connect(self.loader.camera_done)
        self.loader.show_camera.connect(self.show_camera)
        self.loader.done.connect(self.loader_done)
        self.loader.start()

        # for ind, device in enumerate():

    # ----------------------------------------------------------------------
    def loader_done(self):
        self.loader_progress.hide()

    # ----------------------------------------------------------------------
    def show_camera(self, ind, progress):
        camera_settings = self.cameras_settings[ind]
        camera_id = int(camera_settings.get('id'))
        self.loader_progress.set_camera_progress(camera_id, f'Load settings')

        widget = CameraSettings(self, camera_id, camera_settings)
        widget.delete_me.connect(self._delete_camera)
        widget.new_name.connect(self._new_name)
        self._ui.tb_cameras.addTab(widget, camera_settings.get('name'))

        self.loader_progress.set_camera_progress(camera_id, f'done')
        self.loader_progress.total_progress(progress)
        self.camera_done.emit(ind)

    # ----------------------------------------------------------------------
    def _add_camera(self):
        widget = CameraSettings(self, time.time_ns())
        widget.delete_me.connect(self._delete_camera)
        widget.new_name.connect(self._new_name)
        self._ui.tb_cameras.addTab(widget, 'New camera')
        self._ui.tb_cameras.setCurrentIndex(self._ui.tb_cameras.count() - 1)

    # ----------------------------------------------------------------------
    def name_accepted(self, camera_id, new_name):
        existing_names = []
        for ind in range(self._ui.tb_cameras.count()):
            if self._ui.tb_cameras.widget(ind).my_id != camera_id:
                existing_names.append(self._ui.tb_cameras.widget(ind).my_name)

        while new_name in existing_names:
            new_name, accepted = QtWidgets.QInputDialog.getText(self, 'Enter an unique name!', 'Name: ')
            if not accepted:
                return None

        return new_name

    # ----------------------------------------------------------------------
    def _delete_camera(self, id_to_delete):
        tab_to_delete = None
        for ind in range(self._ui.tb_cameras.count()):
            if self._ui.tb_cameras.widget(ind).my_id == id_to_delete:
                tab_to_delete = ind

        if tab_to_delete is not None:
            self._ui.tb_cameras.removeTab(tab_to_delete)

    # ----------------------------------------------------------------------
    def _new_name(self, camera_id, new_name):
        tab_to_rename = None
        for ind in range(self._ui.tb_cameras.count()):
            if self._ui.tb_cameras.widget(ind).my_id == camera_id:
                tab_to_rename = ind

        if tab_to_rename is not None:
            self._ui.tb_cameras.setTabText(tab_to_rename, new_name)

    # ----------------------------------------------------------------------
    def _pick_color(self, source):

        color = QtWidgets.QColorDialog.getColor(getattr(self._ui, source).palette().button().color())

        if color.isValid():
            getattr(self._ui, source).setStyleSheet("QPushButton {background-color: " + f"{color.name()}" + ";}")

    # ----------------------------------------------------------------------
    def _pick_font(self, source):

        font = QtWidgets.QFontDialog.getFont(getattr(self._ui, source).font())

        if font[1]:
            getattr(self._ui, source).setFont(font[0])
            getattr(self._ui, source).setText(font[0].family() + ', ' + str(font[0].pointSize()))

    # ----------------------------------------------------------------------
    def _apply_settings(self):
        general_options = []

        general_options.append(("save_folder", (("path", self._ui.le_save_path.text()),)))

        font = self._ui.cmd_roi_label_font.font()
        general_options.append(('roi', (('font', font.family() + ',' + str(font.pointSize())),
                                     ('fg_color', self._ui.cmd_roi_label_font_color.palette().button().color().name()),
                                     ('bg_color', self._ui.cmd_roi_bkg_color.palette().button().color().name()),
                                     ('fr_color', self._ui.cmd_roi_frame_color.palette().button().color().name()))))

        general_options.append(('marker', (('fr_color', self._ui.cmd_marker_color.palette().button().color().name()),)))

        font = self._ui.cmd_title_font.font()
        general_options.append(('title', (('font', font.family() + ',' + str(font.pointSize())),
                                       ('fg_color', self._ui.cmd_title_font_color.palette().button().color().name()),
                                       ('bg_color', self._ui.cmd_title_bkg_color.palette().button().color().name()))))

        general_options.append(("roi_server", (("enable", 'true' if self._ui.chk_roi_server_enable.isChecked() else 'false'),
                                            ("host", self._ui.le_roi_server_host.text()),
                                            ("port", self._ui.le_roi_server_port.text()))))

        general_options.append(("center_search", (("cross", self._ui.dsb_cross_size.value()),
                                               ("circle", self._ui.dsb_circle_size.value()))))


        cameras_settings = []
        for ind in range(self._ui.tb_cameras.count()):
            settings, need_to_reload = self._ui.tb_cameras.widget(ind).get_data()
            cameras_settings.append(settings)
            if need_to_reload:
                self.cameras_to_reload.append(self._ui.tb_cameras.widget(ind).get_id())

        self._settings.save_new_options(general_options, cameras_settings)

    # ----------------------------------------------------------------------
    def accept(self):

        self._apply_settings()

        QtCore.QSettings(APP_NAME).setValue("{}/geometry".format(self.WIDGET_NAME), self.saveGeometry())

        super(ProgramSetup, self).accept()

    # ----------------------------------------------------------------------
    def reject(self):

        QtCore.QSettings(APP_NAME).setValue("{}/geometry".format(self.WIDGET_NAME), self.saveGeometry())

        super(ProgramSetup, self).reject()

# ----------------------------------------------------------------------
class CameraLoader(QtCore.QThread):
    """
    separate QThread, that loads cameras
    """

    show_camera = QtCore.pyqtSignal('qint64', float)
    done = QtCore.pyqtSignal()

    #----------------------------------------------------------------------
    def __init__(self, main_window):
        super(CameraLoader, self).__init__()

        self.main_window = main_window

        self.done_cameras = []
        self._stop_batch = False

    # ----------------------------------------------------------------------
    def wait_till_camera_done(self, camera_name):
        while camera_name not in self.done_cameras:
            if self._stop_batch:
                break
            self.msleep(100)

    # ----------------------------------------------------------------------
    def interrupt_load(self):
        self._stop_batch = True

    # ----------------------------------------------------------------------
    def run(self):

        total_cameras = len(self.main_window.cameras_settings)
        for ind in range(len(self.main_window.cameras_settings)):
            self.show_camera.emit(ind, ind/total_cameras)
            self.wait_till_camera_done(ind)
            if self._stop_batch:
                break

        self.done.emit()

    # ----------------------------------------------------------------------
    def camera_done(self, camera_name):
        self.done_cameras.append(camera_name)
