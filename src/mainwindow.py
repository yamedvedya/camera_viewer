# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""
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

from src.widgets.base_widget import APP_NAME
from src.widgets.about_dialog import AboutDialog
from src.widgets.camera_widget import CameraWidget
from src.utils.functions import add_dock
from src.utils.functions import (make_log_name, parse_log_level)
from src.utils.xmlsettings import XmlSettings

from src.roisrv.roiserver import RoiServer

from src.gui.MainWindow_ui import Ui_MainWindow


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
        self._init_menu()
        self._load_ui_settings()

        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")
        pg.setConfigOption("leftButtonPan", False)

        self.log, self._log_file, self._log_dir = self._init_logger("cam_logger")

        self.options = options
        self._settings = XmlSettings('./config.xml')
        self._device_list = self._get_cameras_list()
        self._camera_widgets = []
        self._camera_docks = []
        self._add_cameras()

        self._roi_server = []
        if self._settings.has_node('roi_server') and self._settings.option("roi_server", "enable").lower() == "true":
            try:
                self._roi_server = RoiServer(self._settings.option("roi_server", "host"),
                                             self._settings.option("roi_server", "port"))

                self._roi_server.set_camera_device(self._camera_device, self._device_list)
                self._roi_server.start()
                self._roi_server.change_camera.connect(lambda name: self.change_cam(str(name)))
            except Exception as err:
                self.log.exception(err)

        self.setWindowTitle("Camera Viewer ({}@{})".format(getpass.getuser(), socket.gethostname()))

        self._init_status_bar()
        self._status_timer = QtCore.QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status_bar)
        self._status_timer.start(self.STATUS_TICK)

        self.log.info("Initialized successfully")

    # ----------------------------------------------------------------------
    def _get_cameras_list(self):

        cam_list = []
        for device in self._settings.get_nodes('camera_viewer', 'camera'):
            cam_list.append(device.getAttribute('name'))

        if not cam_list:
            raise RuntimeError('No camera profile was found')

        cam_list.sort()

        return cam_list

    # ----------------------------------------------------------------------
    def _add_cameras(self):
        """
        Here we making cameras widgets and docking them
        :return:
        """
        self.setCentralWidget(None)

        self.setDockOptions(QtWidgets.QMainWindow.AnimatedDocks |
                            QtWidgets.QMainWindow.AllowNestedDocks |
                            QtWidgets.QMainWindow.AllowTabbedDocks)

        for camera in self._device_list:
            # try:
            widget, dock = add_dock(self, self.menu_cameras, CameraWidget, f"{camera}", self, self._settings, camera)
            widget.load_ui_settings()
            self._camera_widgets.append(widget)
            self._camera_docks.append(dock)

            # except Exception as err:
            #     open_mgs = QtWidgets.QMessageBox()
            #     open_mgs.setIcon(QtWidgets.QMessageBox.Critical)
            #     open_mgs.setWindowTitle(f"Error")
            #     open_mgs.setText(f"Cannot add {camera}: {err}")
            #     open_mgs.setStandardButtons(QtWidgets.QMessageBox.Ok)
            #     open_mgs.exec_()

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
        self.log.info("Closing the app...")

        for widget in self._camera_widgets:
            widget.clean_close()

        if hasattr(self, '_roi_server') and self._roi_server:
            self.log.info("Stopping ROI server...")
            self._roi_server.stop()

        if hasattr(self, '_status_timer'):
            self._status_timer.stop()

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
        settings = QtCore.QSettings(APP_NAME)

        settings.setValue("MainWindow/geometry", self.saveGeometry())
        settings.setValue("MainWindow/state", self.saveState())

        settings.setValue("AutoScreen", self.auto_screen_action.isChecked())

    # ----------------------------------------------------------------------
    def _load_ui_settings(self):
        """Load basic GUI settings.
        """
        settings = QtCore.QSettings(APP_NAME)

        try:
            self.restoreGeometry(settings.value("MainWindow/geometry"))
        except:
            pass

        try:
            self.restoreState(settings.value("MainWindow/state"))
        except:
            pass

        self._enable_auto_screens = False
        try:
            self._enable_auto_screens = strtobool(settings.value("AutoScreen"))
        except:
            pass

        self.auto_screen_action.setChecked(self._enable_auto_screens)

    # ----------------------------------------------------------------------
    def _init_menu(self):

        self.menu_cameras = QtWidgets.QMenu('Cameras', self)
        self.menuBar().addMenu(self.menu_cameras)

        self.auto_screen_action = QtWidgets.QAction('Enable auto screens', self)
        self.auto_screen_action.setCheckable(True)
        self.menuBar().addAction(self.auto_screen_action)

        about_action = QtWidgets.QAction('About', self)
        about_action.triggered.connect(self._show_about)
        self.menuBar().addAction(about_action)

        quit_action = QtWidgets.QAction('Exit', self)
        quit_action.triggered.connect(self._quit_program)
        self.menuBar().addAction(quit_action)

        # logs display
        # logs_action = QtWidgets.QAction(QtGui.QIcon(":/ico/page.png"), self)
        # logs_action.setToolTip("Show logs")
        # logs_action.setMenu(self._make_log_preview_menu(logs_action))
        #
        # # logs_action.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        # self.menuBar().addAction(self._tbShowLogs)

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
    def _init_status_bar(self):
        """
        """

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


        self.statusBar().addPermanentWidget(lbProcessID)
        self.statusBar().addPermanentWidget(lbCurrentDir)
        self.statusBar().addPermanentWidget(self._lb_resources_status)

    # ----------------------------------------------------------------------
    def _refresh_status_bar(self):
        """
        """
        process = psutil.Process(os.getpid())
        mem = float(process.memory_info().rss) / (1024. * 1024.)
        cpu = psutil.cpu_percent()

        self._lb_resources_status.setText("| {:.2f}MB | CPU {} % |".format(mem,
                                                                           cpu))

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