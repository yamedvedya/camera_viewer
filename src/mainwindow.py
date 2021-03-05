# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""

APP_NAME = "CameraViewer"

import getpass

import logging
import os
import psutil
import socket
import subprocess

from functools import partial

from PyQt5 import QtWidgets, QtCore, QtGui

from distutils.util import strtobool

import pyqtgraph as pg

from src.aboutdialog import AboutDialog
from src.utils.functions import (make_log_name, parse_log_level, refresh_combo_box)
from src.utils.xmlsettings import XmlSettings
from src.utils.errors import report_error
from src.devices.datasource2d import DataSource2D

from src.widgets.frameviewer import FrameViewer
from src.widgets.settingswidget import SettingsWidget

from src.roisrv.roiserver import RoiServer

from src.ui_vimbacam.MainWindow_ui import Ui_MainWindow

# ----------------------------------------------------------------------
class MainWindow(QtWidgets.QMainWindow):
    """
    """
    LOG_PREVIEW = "gvim"
    STATUS_TICK = 2000              # [ms]

    # ----------------------------------------------------------------------
    def __init__(self, options):
        """
        """
        super(MainWindow, self).__init__()
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)

        self.log, self._log_file, self._log_dir = self._init_logger("cam_logger")

        self.options = options
        self._settings = XmlSettings('./config.xml')
        self._device_list = self._parse_settings()

        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")
        pg.setConfigOption("leftButtonPan", False)

        self._init_ui()

        self.camera_name = self._load_ui_settings()
        if self.camera_name == '' or self.camera_name is None or self.camera_name not in self._device_list:
            self.camera_name = self._device_list[0]

        self._camera_device = self._init_data_source()

        self._frame_viewer.set_camera_device(self._camera_device)
        self._settings_widget.set_camera_device(self._camera_device)

        self.change_cam(self.camera_name)
        refresh_combo_box(self._cb_cam_selector, self.camera_name)

        self._statusTimer = QtCore.QTimer(self)
        self._statusTimer.timeout.connect(self._refresh_status_bar)
        self._statusTimer.start(self.STATUS_TICK)

        self._roi_server = []
        if self._settings.option("roi_server", "enable").lower() == "true":
            try:
                self._roi_server = RoiServer(self._settings.option("roi_server", "host"),
                                             self._settings.option("roi_server", "port"))

                self._roi_server.set_camera_device(self._camera_device, self._device_list)
                self._roi_server.start()
                self._roi_server.change_camera.connect(lambda name: self.change_cam(str(name)))
            except Exception as err:
                self.log.exception(err)

        self._refresh_title()
        self.log.info("Initialized successfully")

    # ----------------------------------------------------------------------
    def _parse_settings(self):

        cam_list = []
        for device in self._settings.getNodes('camera_viewer', 'camera'):
            cam_list.append(device.getAttribute('name'))

        if not cam_list:
            raise RuntimeError('No camera profile was found')

        cam_list.sort()

        return cam_list

    # ----------------------------------------------------------------------
    def _init_data_source(self):
        """
        """
        try:
            data_source = DataSource2D(self._settings, self)
            data_source.newFrame.connect(self._frame_viewer.refresh_view)
            data_source.gotError.connect(lambda err_msg: report_error(err_msg, self.log, self, True))
            return data_source

        except Exception as err:
            report_error(err, self.log, self)
            return None

    # ----------------------------------------------------------------------
    def _init_ui(self):
        """
        """
        self.setCentralWidget(None)

        self.setDockOptions(QtWidgets.QMainWindow.AnimatedDocks |
                            QtWidgets.QMainWindow.AllowNestedDocks |
                            QtWidgets.QMainWindow.AllowTabbedDocks)

        self._frame_viewer, self._frameViewerDock = \
            self._addDock(FrameViewer, "Frame", QtCore.Qt.LeftDockWidgetArea, self._settings, self)

        self._settings_widget, self._settingsDock = \
            self._addDock(SettingsWidget, "General", QtCore.Qt.RightDockWidgetArea, self._settings, self)

        self._frame_viewer.status_changed.connect(self._display_camera_status)
        self._frame_viewer.cursor_moved.connect(self._viewer_cursor_moved)
        self._frame_viewer.refresh_numbers.connect(self._settings_widget.refresh_view)

        self._settings_widget.refresh_image.connect(self._frame_viewer.refresh_image)

        self._init_actions()
        self._toolBar = self._init_tool_bar()
        self.addToolBar(self._toolBar)
        self._init_status_bar()

    # ----------------------------------------------------------------------
    def change_cam(self, name):

        self._frame_viewer.stop_live_mode()
        self._settings_widget.close_camera(self._chk_auto_screens.isChecked())
        self._camera_device.close_camera()

        if self._camera_device.new_device_proxy(name) and \
                self._settings_widget.set_new_camera(self._chk_auto_screens.isChecked()) and \
                self._frame_viewer.set_new_camera():
            self.camera_name = name
            refresh_combo_box(self._cb_cam_selector, self.camera_name)
            self.log.info("Changing camera to {}".format(self.camera_name))
        else:
            self._camera_device.new_device_proxy(self.camera_name)
            self._settings_widget.set_new_camera(self._chk_auto_screens.isChecked())
            self._frame_viewer.set_new_camera()
            refresh_combo_box(self._cb_cam_selector, self.camera_name)

            report_error('Cannot change camera', self.log, self, True)

        self._frame_viewer.update_camera_label()
        self._frame_viewer.start_stop_live_mode()
        self._frame_viewer.refresh_image()
        self._refresh_title()

    # ----------------------------------------------------------------------
    def _addDock(self, WidgetClass, label, location, *args, **kwargs):
        """
        """
        widget = WidgetClass(*args, **kwargs)

        dock = QtWidgets.QDockWidget(label)
        dock.setObjectName("{0}Dock".format("".join(label.split())))
        dock.setWidget(widget)

        self.addDockWidget(location, dock)
        self._ui.menuView.addAction(dock.toggleViewAction())

        return widget, dock

    # ----------------------------------------------------------------------
    def _display_camera_status(self, fps):
        """
        """
        self._lb_fps.setText("{:.2f} FPS".format(fps))

    # ----------------------------------------------------------------------
    def _viewer_cursor_moved(self, x, y):
        """
        """
        self._lbCursorPos.setText("({:.2f}, {:.2f})".format(x, y))

    # ----------------------------------------------------------------------
    def _refresh_title(self):
        """
        """
        self.setWindowTitle("{} ({}@{})".format(self.camera_name,       #self.options.cameraID,
                                                getpass.getuser(),
                                                socket.gethostname()))

    # ----------------------------------------------------------------------
    def show_settings_dialog(self):
        """
        """
        self._frame_viewer.stop_live_mode()
        print("Not yet implemented")

    # ----------------------------------------------------------------------
    def _show_log_file(self, logType="main"):
        """

        logType: main, stdout, stderr
        """
        camera = self._settings.option("device", "name")     #self.options.cameraID

        f = self._log_file
        if logType == "stdout":
            f = os.path.join("logs", "stdout_{}.log".format(camera))
        elif logType == "stderr":
            f = os.path.join("logs", "stderr_{}.log".format(camera))

        subprocess.Popen([self.LOG_PREVIEW, f])

    # ----------------------------------------------------------------------
    def _show_about(self):
        """
        """
        self._frame_viewer.stop_live_mode()
        AboutDialog(self).exec_()

    # ----------------------------------------------------------------------
    def closeEvent(self, event):
        """
        """
        if self.clean_close():
            event.accept()
        else:
            event.ignore()

    # ----------------------------------------------------------------------
    def clean_close(self):
        """
        """
        self._settings_widget.close_camera(self._chk_auto_screens.isChecked())

        self.log.info("Closing the app...")

        self._frame_viewer.close()
        if self._roi_server:
            self._roi_server.stop()
        self._settings_widget.close()
        self._statusTimer.stop()
        self._camera_device.close_camera()

        self._save_ui_settings()

        QtWidgets.qApp.clipboard().clear()
        self.log.info("Closed properly")

        return True

    # ----------------------------------------------------------------------
    def _quit_program(self):
        """
        """
        if self.clean_close():
            QtWidgets.qApp.quit()
            # pass

    # ----------------------------------------------------------------------
    def _save_ui_settings(self):
        """Save basic GUI settings.
        """
        settings = QtCore.QSettings(APP_NAME, self.options.beamlineID)

        settings.setValue("MainWindow/geometry", self.saveGeometry())
        settings.setValue("MainWindow/state", self.saveState())

        settings.setValue("LastCamera", self.camera_name)
        settings.setValue("AutoScreen", self._chk_auto_screens.isChecked())

        self._frame_viewer.save_ui_settings(settings)
        self._settings_widget.save_ui_settings(settings)

    # ----------------------------------------------------------------------
    def _load_ui_settings(self):
        """Load basic GUI settings.
        """
        settings = QtCore.QSettings(APP_NAME, self.options.beamlineID)

        try:
            self.restoreGeometry(settings.value("MainWindow/geometry"))
        except:
            pass

        try:
            self.restoreState(settings.value("MainWindow/state"))
        except:
            pass

        try:
            self._chk_auto_screens.setChecked(strtobool(settings.value("AutoScreen")))
        except:
            self._chk_auto_screens.setChecked(False)

        self._frame_viewer.load_ui_settings(settings)
        self._settings_widget.load_ui_settings(settings)

        try:
            return settings.value("LastCamera")
        except:
            return None

    # ----------------------------------------------------------------------
    def _init_actions(self):
        """
        """
        self._ui.actionQuit.triggered.connect(self._quit_program)
        about_action = QtWidgets.QAction('About', self)
        about_action.triggered.connect(self._show_about)
        self.menuBar().addAction(about_action)

        self._actionStartStop = QtWidgets.QAction(self)
        self._actionStartStop.setIcon(QtGui.QIcon(":/ico/play_16px.png"))
        self._actionStartStop.setText("Start/Stop")
        self._actionStartStop.triggered.connect(self._frame_viewer.start_stop_live_mode)

        self._actionPrintImage = QtWidgets.QAction(self)
        self._actionPrintImage.setIcon(QtGui.QIcon(":/ico/print.png"))
        self._actionPrintImage.setText("Print Image")
        self._actionPrintImage.triggered.connect(self._frame_viewer.print_image)
        self._actionPrintImage.setEnabled(False)

        self._actionCopyImage = QtWidgets.QAction(self)
        self._actionCopyImage.setIcon(QtGui.QIcon(":/ico/copy.png"))
        self._actionCopyImage.setText("Copy to Clipboard")
        self._actionCopyImage.triggered.connect(self._frame_viewer.to_clipboard)

        self._actionShowSettings = QtWidgets.QAction(self)
        self._actionShowSettings.setIcon(QtGui.QIcon(":/ico/settings.png"))
        self._actionShowSettings.setText("Settings")
        self._actionShowSettings.triggered.connect(self.show_settings_dialog)

    # ----------------------------------------------------------------------
    def _make_save_menu(self, parent):
        """
        Args:
            parent (QWidget)
        """
        saveMenu = QtWidgets.QMenu(parent)

        self._saveImgAction = saveMenu.addAction("Image")
        self._saveImgAction.triggered.connect(self._frame_viewer.save_to_image)

        self._saveAsciiAction = saveMenu.addAction("ASCII")
        self._saveAsciiAction.triggered.connect(partial(self._frame_viewer.save_to_file,
                                                        fmt="csv"))

        self._saveNumpyAction = saveMenu.addAction("Numpy")
        self._saveNumpyAction.triggered.connect(partial(self._frame_viewer.save_to_file,
                                                        fmt="npy"))
        return saveMenu

    # ----------------------------------------------------------------------
    def _make_log_preview_menu(self, parent):
        """
        Args:
            parent (QWidget)
        """
        logMenu = QtWidgets.QMenu(parent)

        self._mainLogAction = logMenu.addAction("Logfile")
        self._mainLogAction.triggered.connect(partial(self._show_log_file,
                                                      logType="main"))
        logMenu.addSeparator()

        self._stdoutLogAction = logMenu.addAction("Stdout")
        self._stdoutLogAction.triggered.connect(partial(self._show_log_file,
                                                        logType="stdout"))

        self._stderrLogAction = logMenu.addAction("Stderr")
        self._stderrLogAction.triggered.connect(partial(self._show_log_file,
                                                        logType="stderr"))
        return logMenu

    # ----------------------------------------------------------------------
    def _init_tool_bar(self):
        """
        """
        if hasattr(self, '_toolBar'):
            toolBar = self._toolBar
        else:
            toolBar = QtWidgets.QToolBar("Main toolbar", self)
            toolBar.setObjectName("VimbaCam_ToolBar")

        self._cb_cam_selector = QtWidgets.QComboBox()
        self._cb_cam_selector.addItems(self._device_list)
        self._cb_cam_selector.currentIndexChanged.connect(lambda: self.change_cam(self._cb_cam_selector.currentText()))
        toolBar.addWidget(self._cb_cam_selector)

        toolBar.addAction(self._actionStartStop)
        toolBar.addSeparator()

            # image saving
        self._tbSaveScan = QtWidgets.QToolButton(self)
        self._tbSaveScan.setIcon(QtGui.QIcon(":/ico/save.png"))
        self._tbSaveScan.setToolTip("Save")

        self._saveMenu = self._make_save_menu(self._tbSaveScan)
        self._tbSaveScan.setMenu(self._saveMenu)
        self._tbSaveScan.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        toolBar.addWidget(self._tbSaveScan)

        toolBar.addAction(self._actionPrintImage)
        toolBar.addAction(self._actionCopyImage)
        toolBar.addSeparator()

        toolBar.addAction(self._actionShowSettings)

        toolBar.addSeparator()

            # logs display
        self._tbShowLogs = QtWidgets.QToolButton(self)
        self._tbShowLogs.setIcon(QtGui.QIcon(":/ico/page.png"))
        self._tbShowLogs.setToolTip("Show logs")

        self._logShowMenu = self._make_log_preview_menu(self._tbShowLogs)
        self._tbShowLogs.setMenu(self._logShowMenu)
        self._tbShowLogs.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        toolBar.addWidget(self._tbShowLogs)

        toolBar.addSeparator()
        self._chk_auto_screens = QtWidgets.QCheckBox(self)
        self._chk_auto_screens.setText('Enable auto screens')
        toolBar.addWidget(self._chk_auto_screens)

        return toolBar

    # ----------------------------------------------------------------------
    def _init_status_bar(self):
        """
        """
        self._lbCursorPos = QtWidgets.QLabel("")

        processID = os.getpid()
        currentDir = os.getcwd()

        lbProcessID = QtWidgets.QLabel("PID {}".format(processID))
        lbProcessID.setStyleSheet("QLabel {color: #000066;}")
        lbCurrentDir = QtWidgets.QLabel("{}".format(currentDir))

            # resource usage
        process = psutil.Process(processID)
        mem = float(process.memory_info().rss) / (1024. * 1024.)
        cpu = process.cpu_percent()

        self._lb_resources_status = QtWidgets.QLabel("| {:.2f}MB | CPU {} % |".format(mem, cpu))

        self.statusBar().addPermanentWidget(self._lbCursorPos)
        self.statusBar().addPermanentWidget(lbProcessID)
        self.statusBar().addPermanentWidget(lbCurrentDir)
        self.statusBar().addPermanentWidget(self._lb_resources_status)

        self._lb_fps = QtWidgets.QLabel("FPS: -")
        self._lb_fps.setMinimumWidth(70)
        self.statusBar().addPermanentWidget(self._lb_fps)

    # ----------------------------------------------------------------------
    def _refresh_status_bar(self):
        """
        """
        process = psutil.Process(os.getpid())
        mem = float(process.memory_info().rss) / (1024. * 1024.)
        cpu = psutil.cpu_percent()

        self._lb_resources_status.setText("| {:.2f}MB | CPU {} % |".format(mem,
                                                                           cpu))

        if self._camera_device.is_running():
            self._actionStartStop.setIcon(QtGui.QIcon(":/ico/stop.png"))
        else:
            self._actionStartStop.setIcon(QtGui.QIcon(":/ico/play_16px.png"))

        self._settings_widget.refresh_view()

    # ----------------------------------------------------------------------
    def _init_logger(self, loggerName):
        """Initialize logging object

        Args:
            loggerName (str)
        """
        log = logging.getLogger(loggerName)

        level = parse_log_level("debug")
        log.setLevel(level)

        self.formatter = logging.Formatter("%(asctime)s %(module)s %(lineno)-6d %(levelname)-6s %(message)s")

        logFile, logDir = make_log_name("vimbaviewer", "logs")

        fh = logging.FileHandler(logFile)
        fh.setFormatter(self.formatter)
        log.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(self.formatter)
        log.addHandler(ch)

        print("{}\nIn case of problems look at: {}\n{}".format(
              "=" * 100, logFile, "=" * 100))

        return log, logFile, logDir