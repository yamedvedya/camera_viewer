# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""

import getpass
import shutil
import logging
import os
import psutil
import socket
import pyqtgraph as pg
from pathlib import Path

from PyQt5 import QtWidgets, QtCore

from distutils.util import strtobool

from petra_camera.widgets.about_dialog import AboutDialog
from petra_camera.widgets.general_settings import ProgramSetup
from petra_camera.widgets.camera_widget import CameraWidget
from petra_camera.widgets.empty_camera_widget import EmptyCameraWidget
from petra_camera.utils.xmlsettings import XmlSettings
from petra_camera.widgets.import_cameras import ImportCameras
from petra_camera.widgets.batch_progress import BatchProgress
from petra_camera.roisrv.roiserver import RoiServer

from petra_camera.gui.MainWindow_ui import Ui_MainWindow

from petra_camera.constants import APP_NAME
logger = logging.getLogger(APP_NAME)


# ----------------------------------------------------------------------
class PETRACamera(QtWidgets.QMainWindow):
    """
    """
    LOG_PREVIEW = "gvim"
    STATUS_TICK = 3000              # [ms]

    camera_done = QtCore.pyqtSignal(str)
    camera_closed = QtCore.pyqtSignal(str)

    # ----------------------------------------------------------------------
    def __init__(self, options):
        """
        """
        super(PETRACamera, self).__init__()
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)

        self._init_menu()

        self.loader_progress = BatchProgress()
        self.loader_progress.stop_batch.connect(self.interrupt_batch)

        self.loader = None
        self.cameras_to_reload = []
        self.cameras_to_delete = []
        self.cameras_to_add = []

        self.close_requested = False

        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")
        pg.setConfigOption("leftButtonPan", False)

        self.options = options
        self.settings = self.get_settings(options)

        self.setCentralWidget(None)

        self.setDockOptions(QtWidgets.QMainWindow.AnimatedDocks |
                            QtWidgets.QMainWindow.AllowNestedDocks |
                            QtWidgets.QMainWindow.AllowTabbedDocks)

        self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtWidgets.QTabWidget.North)

        self.camera_widgets = {}
        self.camera_docks = {}

        self.camera_list = self.get_cameras()

        logger.debug(f"Start loader for cameras: {self.camera_list}")

        # first we reset progress bar
        self.loader_progress.clear()
        self.loader_progress.set_titel('Open cameras')
        self.loader_progress.show()

        self.loader = CameraLoader(self, 'open')
        self.camera_done.connect(self.loader.camera_done)
        self.loader.add_camera.connect(self.add_camera)
        self.loader.done.connect(self.loader_done)
        self.loader.start()

        self._roi_server = None
        self.start_server()

        self.setWindowTitle("Camera Viewer ({}@{})".format(getpass.getuser(), socket.gethostname()))

        self._init_status_bar()
        self._load_ui_settings()

        self._status_timer = QtCore.QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status_bar)
        self._status_timer.start(self.STATUS_TICK)

        logger.info("Initialized successfully")

    # ----------------------------------------------------------------------
    def interrupt_batch(self):
        self.loader.interrupt_batch()

    # ----------------------------------------------------------------------
    def loader_done(self):
        self.loader_progress.hide()

        if self.close_requested:
            logger.info("Closed properly")
            QtWidgets.qApp.quit()

        self.camera_list = self.get_cameras()

    # ----------------------------------------------------------------------
    def add_camera(self, camera_name, progress):
        """
        """

        self.loader_progress.set_progress(f'Open camera {camera_name}', progress)

        dock = QtWidgets.QDockWidget(camera_name)
        dock.setObjectName(f'{"".join(camera_name.split())}Dock')

        children = [child for child in self.findChildren(QtWidgets.QDockWidget)
                    if isinstance(child.widget(), CameraWidget)]
        if children:
            self.tabifyDockWidget(children[-1], dock)
        else:
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)

        self.menu_cameras.addAction(dock.toggleViewAction())
        dock.setStyleSheet("""QDockWidget {font-size: 14pt; font-weight: bold;}""")
        self.camera_docks[camera_name] = dock

        try:
            widget = CameraWidget(self, camera_name)
            widget.load_ui_settings()

        except Exception as err:

            widget = EmptyCameraWidget(self, camera_name, f'{err}')
            widget.reinit_camera.connect(self._reinit_camera)
            widget.load_ui_settings()

            open_mgs = QtWidgets.QMessageBox()
            open_mgs.setIcon(QtWidgets.QMessageBox.Critical)
            open_mgs.setWindowTitle(f"Error")
            open_mgs.setText(f"Cannot add {camera_name}:\n{err}")
            open_mgs.setStandardButtons(QtWidgets.QMessageBox.Ok)
            open_mgs.exec_()

        self.camera_widgets[camera_name] = widget
        dock.setWidget(widget)

        self.camera_done.emit(camera_name)

    # ----------------------------------------------------------------------
    def _reinit_camera(self, camera_name):
        if camera_name in self.camera_widgets:
            del self.camera_widgets[camera_name]
        if camera_name in self.camera_docks:
            del self.camera_docks[camera_name]

        try:
            widget = CameraWidget(self, camera_name)
            widget.load_ui_settings()
            self.camera_widgets[camera_name] = widget
            self.camera_docks[camera_name].setWidget(widget)

        except Exception as err:

            open_mgs = QtWidgets.QMessageBox()
            open_mgs.setIcon(QtWidgets.QMessageBox.Critical)
            open_mgs.setWindowTitle(f"Error")
            open_mgs.setText(f"Cannot add {camera_name}:\n{err}")
            open_mgs.setStandardButtons(QtWidgets.QMessageBox.Ok)
            open_mgs.exec_()

    # ----------------------------------------------------------------------
    def start_server(self):

        if self.settings.has_node('roi_server') and self.settings.option("roi_server", "enable").lower() == "true":
            try:
                self._roi_server = RoiServer(self.settings.option("roi_server", "host"),
                                             self.settings.option("roi_server", "port"),
                                             self.camera_list)
                self._roi_server.start()
            except Exception as err:
                logger.exception(err)

    # ----------------------------------------------------------------------
    def _show_about(self):
        """
        """
        AboutDialog(self).exec_()

    # ----------------------------------------------------------------------
    def show_settings(self):

        existing_cameras = self.camera_list
        self.cameras_to_reload = []
        self.cameras_to_delete = []
        self.cameras_to_add = []

        dlg = ProgramSetup(self)
        if dlg.exec_():
            logger.info("Applying new settings...")
            self.camera_list = self._get_cameras_list()

            self.cameras_to_reload = dlg.cameras_to_reload
            self.cameras_to_add = dlg.cameras_to_add
            self.cameras_to_delete = list(set(existing_cameras)-set(self.camera_list))
            if self.cameras_to_reload or self.cameras_to_delete:
                self.loader_progress.clear()
                self.loader_progress.set_titel('Applying new settings')
                self.loader_progress.show()

                self.loader = CameraLoader(self, 'reload')
                self.camera_done.connect(self.loader.camera_done)
                self.loader.add_camera.connect(self.add_camera)
                self.loader.close_camera.connect(self.close_camera)
                self.loader.reload_camera.connect(self.reload_camera)
                self.loader.done.connect(self.loader_done)

                self.loader.start()

    # ----------------------------------------------------------------------
    def reload_camera(self, camera_name, progress):

        self.loader_progress.set_progress(f'Reloading camera {camera_name}', progress)

        self.camera_widgets[camera_name].clean_close()

        try:
            widget = CameraWidget(self, camera_name)
            widget.load_ui_settings()

        except Exception as err:

            widget = EmptyCameraWidget(self, camera_name, f'{err}')
            widget.reinit_camera.connect(self._reinit_camera)
            widget.load_ui_settings()

            open_mgs = QtWidgets.QMessageBox()
            open_mgs.setIcon(QtWidgets.QMessageBox.Critical)
            open_mgs.setWindowTitle(f"Error")
            open_mgs.setText(f"Cannot add {camera_name}:\n{err}")
            open_mgs.setStandardButtons(QtWidgets.QMessageBox.Ok)
            open_mgs.exec_()

        self.camera_docks[camera_name].setWidget(widget)
        self.camera_widgets[camera_name] = widget
        self.camera_done.emit(camera_name)

    # ----------------------------------------------------------------------
    def close_camera(self, camera_name, progress):

        self.loader_progress.set_progress(f'Closing camera {camera_name}', progress)

        try:
            self.camera_widgets[camera_name].clean_close()
            self.removeDockWidget(self.camera_docks[camera_name])
            if camera_name in self.camera_widgets:
                del self.camera_widgets[camera_name]
            if camera_name in self.camera_docks:
                del self.camera_docks[camera_name]
        except Exception as err:
            logger.error(f'Error while closing camera {camera_name} :{repr(err)}')

        self.camera_done.emit(camera_name)

    # ----------------------------------------------------------------------
    def clean_close(self):
        """
        """
        logger.info("Closing the app...")

        if self._roi_server is not None:
            logger.info("Stopping ROI server...")
            self._roi_server.stop()

        if hasattr(self, '_status_timer'):
            self._status_timer.stop()

        self._save_ui_settings()

        QtWidgets.qApp.clipboard().clear()

        self.loader_progress.clear()
        self.loader_progress.set_titel('Closing cameras')
        self.loader_progress.show()

        self.close_requested = True

        self.loader = CameraLoader(self, 'close')
        self.camera_done.connect(self.loader.camera_done)
        self.loader.close_camera.connect(self.close_camera)
        self.loader.done.connect(self.loader_done)
        self.loader.start()

    # ----------------------------------------------------------------------
    def closeEvent(self, event):
        """
        """
        event.ignore()
        self.clean_close()

    # ----------------------------------------------------------------------
    def _quit_program(self):
        """
        """
        self.clean_close()
            # pass

    # ----------------------------------------------------------------------
    def reset_settings(self):

        home = os.path.join(str(Path.home()), '.petra_camera')
        shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'default_config.xml'),
                    os.path.join(home, 'default.xml'))
        self.settings = XmlSettings(os.path.join(home, 'default.xml'))

    # ----------------------------------------------------------------------
    def get_settings(self, options):

        home = os.path.join(str(Path.home()), '.petra_camera')
        file_name = str(options.profile)
        if not file_name.endswith('.xml'):
            file_name += '.xml'

        if not os.path.exists(home):
            os.mkdir(home)

        if file_name != 'default.xml':
            if not os.path.exists(os.path.join(home, file_name)):
                file = QtWidgets.QFileDialog.getOpenFileName(self, 'Cannot find settings file, please locate it',
                                                             str(Path.home()), 'XML settings (*.xml)')
                if file[0]:
                    shutil.copy(file[0], os.path.join(home, 'default.xml'))
            else:
                shutil.copy(os.path.join(home, file_name), os.path.join(home, 'default.xml'))

        if not os.path.exists(os.path.join(home, 'default.xml')):
            shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'default_config.xml'),
                        os.path.join(home, 'default.xml'))

        return XmlSettings(os.path.join(home, 'default.xml'))

    # ----------------------------------------------------------------------
    def _get_cameras_list(self):

        cam_list = []
        for device in self.settings.get_nodes('camera'):
            if 'enabled' in device.keys():
                if strtobool(device.get('enabled')):
                    cam_list.append(device.get('name'))
            else:
                cam_list.append(device.get('name'))

        cam_list.sort()

        return cam_list

    # ----------------------------------------------------------------------
    def get_cameras(self):

        cam_list = self._get_cameras_list()

        if len(cam_list) < 1:
            dlg = ImportCameras(self.settings)
            dlg.exec_()
            cam_list = self._get_cameras_list()

        return cam_list

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

        enable_auto_screens = False
        try:
            enable_auto_screens = strtobool(settings.value("AutoScreen"))
        except:
            pass

        self.auto_screen_action.setChecked(enable_auto_screens)
        self._display_auto_screens(enable_auto_screens)

    # ----------------------------------------------------------------------
    def _display_auto_screens(self, state):
        font = self.auto_screen_action.font()

        if state:
            self.auto_screen_action.setText('Auto screens ENABLED')
        else:
            self.auto_screen_action.setText('Auto screens DISABLED')

        font.setBold(state)
        self.auto_screen_action.setFont(font)

    # ----------------------------------------------------------------------
    def _init_menu(self):

        self.menu_cameras = QtWidgets.QMenu('Cameras', self)
        self.menuBar().addMenu(self.menu_cameras)

        settings = QtWidgets.QAction('Program settings', self)
        settings.triggered.connect(self.show_settings)
        self.menuBar().addAction(settings)

        self.auto_screen_action = QtWidgets.QAction('', self)
        self.auto_screen_action.setCheckable(True)
        self.auto_screen_action.triggered.connect(self._display_auto_screens)
        self.menuBar().addAction(self.auto_screen_action)

        about_action = QtWidgets.QAction('About', self)
        about_action.triggered.connect(self._show_about)
        self.menuBar().addAction(about_action)

        quit_action = QtWidgets.QAction('Exit', self)
        quit_action.triggered.connect(self._quit_program)
        self.menuBar().addAction(quit_action)

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
class CameraLoader(QtCore.QThread):
    """
    separate QThread, that loads cameras
    """

    add_camera = QtCore.pyqtSignal(str, float)
    close_camera = QtCore.pyqtSignal(str, float)
    reload_camera = QtCore.pyqtSignal(str, float)
    done = QtCore.pyqtSignal()

    #----------------------------------------------------------------------
    def __init__(self, main_window, mode):
        super(CameraLoader, self).__init__()

        self.main_window = main_window
        self.mode = mode

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

        if self.mode in ['open', 'close']:
            total_cameras = float(len(self.main_window.camera_list))
            if self.mode == 'open':
                signal = self.add_camera
            else:
                signal = self.close_camera

            for ind, camera_name in enumerate(self.main_window.camera_list):
                signal.emit(camera_name, ind/total_cameras)
                self.wait_till_camera_done(camera_name)
                if self._stop_batch:
                    break

        else:
            total_cameras = len(self.main_window.cameras_to_reload) +\
                            len(self.main_window.cameras_to_delete) +\
                            len(self.main_window.cameras_to_add)
            counter = 0

            for camera_name in self.main_window.cameras_to_delete:
                self.close_camera.emit(camera_name, counter / total_cameras)
                self.wait_till_camera_done(camera_name)
                if self._stop_batch:
                    break

            if not self._stop_batch:
                for camera_name in self.main_window.cameras_to_reload:
                    self.reload_camera.emit(camera_name, counter / total_cameras)
                    self.wait_till_camera_done(camera_name)
                    if self._stop_batch:
                        break
                    counter += 1

            if not self._stop_batch:
                for camera_name in self.main_window.cameras_to_add:
                    self.add_camera.emit(camera_name, counter / total_cameras)
                    self.wait_till_camera_done(camera_name)
                    if self._stop_batch:
                        break
                    counter += 1

        self.done.emit()

    # ----------------------------------------------------------------------
    def camera_done(self, camera_name):
        self.done_cameras.append(camera_name)
