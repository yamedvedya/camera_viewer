# Created by matveyev at 22.02.2022

import logging

from PyQt5 import QtWidgets, QtGui, QtCore

from petra_camera.main_window import APP_NAME
from petra_camera.gui.SettingsDialog_ui import Ui_SettingsDialog

WIDGET_NAME = 'ProgramSetup'

logger = logging.getLogger(APP_NAME)


class ProgramSetup(QtWidgets.QDialog):

    # ----------------------------------------------------------------------
    def __init__(self, main_window):
        """
        """
        super(ProgramSetup, self).__init__()
        self._ui = Ui_SettingsDialog()
        self._ui.setupUi(self)

        self._main_window = main_window

        self._setting = main_window.settings

        # self._ui.cmd_sav_profile.clicked.connect(self._save_settings)
        # self._ui.cmd_load_profile.clicked.connect(self._load_settings)

        self._ui.cmd_save_folder.clicked.connect(self._new_save_folder)

        # self._ui.cmd_roi_frame_color.clicked.connect(lambda: self._pick_color('cmd_roi_frame_color'))
        # self._ui.cmd_roi_bkg_color.clicked.connect(lambda: self._pick_color('cmd_roi_bkg_color'))
        # self._ui.cmd_marker_color.clicked.connect(lambda: self._pick_color('cmd_marker_color'))
        # self._ui.cmd_title_bkg_color.clicked.connect(lambda: self._pick_color('cmd_title_bkg_color'))

        self._display_settings()

    # ----------------------------------------------------------------------
    def _new_save_folder(self):

        folder = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select safe folder', self._ui.le_save_path.text())
        if folder:
            self._ui.le_save_path.setText(folder)

    # ----------------------------------------------------------------------
    def _display_settings(self):
        self._ui.le_save_path.setText(self._setting.option("save_folder", "default"))

        self._ui.cmd_roi_frame_color.setStyleSheet("QPushButton {background-color: " +
                                                   f"{self._setting.option('roi', 'fr_color')}" + ";}")

        self._ui.cmd_roi_label_color.setStyleSheet("QPushButton {background-color: " +
                                                   f"{self._setting.option('roi', 'fg_color')}" + ";}")
        self._ui.cmd_roi_label_color.setText(self._setting.option('roi', 'font'))
        self._ui.cmd_roi_bkg_color.setStyleSheet("QPushButton {background-color: " +
                                                 f"{self._setting.option('roi', 'bg_color')}" + ";}")

        self._ui.cmd_marker_color.setStyleSheet("QPushButton {background-color: "+
                                                f"{self._setting.option('marker', 'fr_color')}" + ";}")

        self._ui.cmd_title_font_color.setStyleSheet("QPushButton {background-color: " +
                                                    f"{self._setting.option('title', 'fg_color')}" + ";}")
        self._ui.cmd_title_font_color.setText(self._setting.option('title', 'font'))
        self._ui.cmd_title_bkg_color.setStyleSheet("QPushButton {background-color: " +
                                                   f"{self._setting.option('title', 'bg_color')}" + ";}")

        if self._setting.has_node('roi_server') and self._setting.option("roi_server", "enable").lower() == "true":
            self._ui.chk_roi_server_enable.setChecked(True)
            self._ui.le_roi_server_host.setEnabled(True)
            self._ui.le_roi_server_host.setText(self._setting.option("roi_server", "host"))
            self._ui.le_roi_server_port.setEnabled(True)
            self._ui.le_roi_server_port.setText(self._setting.option("roi_server", "port"))
        else:
            self._ui.chk_roi_server_enable.setChecked(False)
            self._ui.le_roi_server_host.setEnabled(False)
            self._ui.le_roi_server_host.setEnabled(False)

        self._ui.dsb_cross_size.setValue(float(self._setting.option("center_search", "cross")))
        self._ui.dsb_circle_size.setValue(float(self._setting.option("center_search", "circle")))

    color = QtWidgets.QColorDialog.getColor()

    # # ----------------------------------------------------------------------
    # def _pick_color(self, source):
    #
    #     color = QtWidgets.QColorDialog.getColor(QtGui.QColor())
    #
    #     if color.isValid():
    #         self._camera_device.set_marker_value(self.my_id, 'color', color.name())
    #         self.repaint_marker.emit()

    # ----------------------------------------------------------------------
    def accept(self):

        # self._main_window.apply_settings()

        QtCore.QSettings(APP_NAME).setValue("{}/geometry".format(WIDGET_NAME), self.saveGeometry())

        super(ProgramSetup, self).accept()

    # ----------------------------------------------------------------------
    def reject(self):

        QtCore.QSettings(APP_NAME).setValue("{}/geometry".format(WIDGET_NAME), self.saveGeometry())

        super(ProgramSetup, self).reject()