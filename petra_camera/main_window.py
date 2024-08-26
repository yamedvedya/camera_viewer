# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""
"""

import getpass
import shutil
import logging
import os
import time

import numpy as np
import psutil
import socket
import pyqtgraph as pg
from pathlib import Path

from PyQt5 import QtWidgets, QtCore, QtGui

from distutils.util import strtobool

from queue import Queue, Empty
from threading import Event

from petra_camera.widgets.about_dialog import AboutDialog
from petra_camera.widgets.general_settings import ProgramSetup
from petra_camera.widgets.camera_widget import CameraWidget, CustomTitleBar
from petra_camera.widgets.empty_camera_widget import EmptyCameraWidget
from petra_camera.utils.xmlsettings import XmlSettings
from petra_camera.widgets.import_cameras import ImportCameras
from petra_camera.widgets.batch_progress import BatchProgress
from petra_camera.roisrv.roiserver import RoiServer
from petra_camera.devices.datasource2d import DataSource2D

from petra_camera.gui.MainWindow_ui import Ui_MainWindow

from petra_camera.constants import APP_NAME

logger = logging.getLogger(APP_NAME)

N_WORKERS = 3


# ----------------------------------------------------------------------
class PETRACamera(QtWidgets.QMainWindow):
    """
    """
    LOG_PREVIEW = "gvim"
    STATUS_TICK = 500  # [ms]

    job_done = QtCore.pyqtSignal(object)

    # ----------------------------------------------------------------------
    def __init__(self, options):
        """
        """
        super(PETRACamera, self).__init__()
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)

        self.init_finished = False

        self._init_menu()

        self.loader_progress = BatchProgress()

        self.close_requested = False

        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")
        pg.setConfigOption("leftButtonPan", False)

        self.options = options
        self.settings = self.load_settings(options)

        self.setCentralWidget(None)

        self.setDockOptions(QtWidgets.QMainWindow.AnimatedDocks |
                            QtWidgets.QMainWindow.AllowNestedDocks |
                            QtWidgets.QMainWindow.AllowTabbedDocks)

        self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtWidgets.QTabWidget.North)

        self.camera_widgets = {}
        self.camera_docks = {}
        self.camera_dock_title = {}
        self.camera_devices = {}

        self.camera_list = self.get_cameras()

        logger.debug(f"Start loader for cameras: {self.camera_list}")

        # first we reset progress bar
        self.loader_progress.clear()
        self.loader_progress.new_cameras_set(list(self.camera_list.items()))
        self.loader_progress.set_title('Open cameras')
        self.loader_progress.show()

        self.loader = BatchLoader(self)
        self.job_done.connect(self.loader.job_done)
        self.loader.add_camera.connect(self.add_camera)
        self.loader.close_camera.connect(self.close_camera)
        self.loader.reload_camera.connect(self.reload_camera)
        self.loader.set_done.connect(self.loader_done)

        self.loader.loader_set_camera_status.connect(self.loader_progress.set_camera_progress)
        self.loader.loader_set_progress.connect(self.loader_progress.total_progress)

        self.loader.start()
        self.loader.new_set_to_be_done(list(self.camera_list.keys()), [], [])

        self._roi_server = None
        self.start_server()

        self.setWindowTitle("Camera Viewer ({}@{})".format(getpass.getuser(), socket.gethostname()))

        self._init_status_bar()

        self._status_timer = QtCore.QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status)
        self._status_timer.start(self.STATUS_TICK)

        logger.info("Initialized successfully")

    # ----------------------------------------------------------------------
    def add_camera(self, camera_id, job_id):
        """
        """
        logger.debug(f"Request to add {camera_id}")
        dock = QtWidgets.QDockWidget(self.camera_list[camera_id], self)
        dock.setObjectName(f'{camera_id}Dock')

        self.camera_docks[camera_id] = dock
        title_widget = CustomTitleBar(dock)
        dock.setTitleBarWidget(title_widget)
        self.camera_dock_title[camera_id] = title_widget

        children = [child for child in self.findChildren(QtWidgets.QDockWidget)
                    if isinstance(child.widget(), (CameraWidget, EmptyCameraWidget))]
        if children:
            self.tabifyDockWidget(children[-1], dock)
        else:
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)

        self.menu_cameras.addAction(dock.toggleViewAction())

        self.make_camera_widget(camera_id)

        logger.debug(f"Opening {camera_id} done")
        self.job_done.emit(job_id)

    # ----------------------------------------------------------------------
    def make_camera_widget(self, camera_id):
        widget, last_err = None, ""
        if self.camera_devices[camera_id].load_status[0]:
            try:
                widget = CameraWidget(self, self.camera_docks[camera_id], self.camera_devices[camera_id])
            except Exception as err:
                logger.error(err, exc_info=True)
                last_err = f'{err}'
        else:
            last_err = self.camera_devices[camera_id].load_status[1]

        if widget is None:
            widget = EmptyCameraWidget(self, camera_id, last_err)
            widget.reinit_camera.connect(self.reinit_camera)

        widget.load_ui_settings()

        self.camera_widgets[camera_id] = widget
        self.camera_docks[camera_id].setWidget(widget)
        self.camera_dock_title[camera_id].setTitle(self.camera_list[camera_id])

    # ----------------------------------------------------------------------
    def reinit_camera(self, camera_id):
        self.camera_widgets[camera_id] = DataSource2D(self.settings, camera_id)
        self.make_camera_widget(camera_id)

    # ----------------------------------------------------------------------
    def reload_camera(self, camera_id, job_id):
        logger.debug(f"Request to reload {camera_id}")
        self.camera_widgets[camera_id].clean_close()
        self.make_camera_widget(camera_id)
        logger.debug(f"Reload {camera_id} done")
        self.job_done.emit(job_id)

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

        dlg = ProgramSetup(self)
        if dlg.exec_():
            logger.info("Applying new settings...")

            self.camera_list = self._get_cameras_list()

            to_add = list(set(self.camera_list) - set(existing_cameras))
            to_close = list(set(existing_cameras) - set(self.camera_list))
            to_reload = dlg.cameras_to_reload

            full_list = to_add + to_close + to_reload
            existing_cameras.update(self.camera_list)

            if len(full_list):
                self.loader_progress.clear()
                self.loader_progress.set_title('Applying new settings')
                self.loader_progress.new_cameras_set([(id, existing_cameras[id]) for id in full_list])
                self.loader_progress.show()

                self.loader.new_set_to_be_done(to_add, to_close, to_reload)

    # ----------------------------------------------------------------------
    def close_camera(self, camera_id, job_id):
        logger.debug(f"Request to close {camera_id}")
        try:
            self.camera_widgets[camera_id].clean_close()
            self.removeDockWidget(self.camera_docks[camera_id])
            if camera_id in self.camera_widgets:
                del self.camera_widgets[camera_id]
            if camera_id in self.camera_docks:
                del self.camera_docks[camera_id]
            if camera_id in self.camera_dock_title:
                del self.camera_dock_title[camera_id]

        except Exception as err:
            logger.error(f'Error while closing camera {self.camera_list[camera_id]} :{repr(err)}', exc_info=True)

        logger.debug(f"Closing {camera_id} done")
        self.job_done.emit(job_id)

    # ----------------------------------------------------------------------
    def loader_done(self):
        self.loader_progress.hide()

        if not self.init_finished:
            self._load_ui_settings()
            self.init_finished = True

        if self.close_requested:
            self.loader.wait_to_safe_close()
            QtWidgets.qApp.quit()

    # ----------------------------------------------------------------------
    def clean_close(self):
        """
        """
        logger.info("Closing the app...")

        QtWidgets.qApp.clipboard().clear()

        if self._roi_server is not None:
            logger.info("Stopping ROI server...")
            self._roi_server.stop()

        if hasattr(self, '_status_timer'):
            self._status_timer.stop()

        self._save_ui_settings()

        self.loader_progress.clear()
        self.loader_progress.new_cameras_set(list(self.camera_list.items()))
        self.loader_progress.set_title('Closing cameras')
        self.loader_progress.show()

        self.close_requested = True

        self.loader.new_set_to_be_done([], list(self.camera_list.keys()), [])

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

    # ----------------------------------------------------------------------
    def reset_settings_to_default(self):

        home = os.path.join(str(Path.home()), '.petra_camera')
        shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'default_config.xml'),
                    os.path.join(home, 'default.xml'))
        self.settings = XmlSettings(os.path.join(home, 'default.xml'))

    # ----------------------------------------------------------------------
    def load_settings(self, options):

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
                    return XmlSettings(file[0])
                else:
                    raise RuntimeError('Cannot load cameras settings')
            else:
                return XmlSettings(os.path.join(home, file_name))

        else:
            if not os.path.exists(os.path.join(home, 'default.xml')):
                shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'default_config.xml'),
                            os.path.join(home, 'default.xml'))

            return XmlSettings(os.path.join(home, 'default.xml'))

    # ----------------------------------------------------------------------
    def _get_cameras_list(self):

        cam_list = {}
        for device in self.settings.get_nodes('camera'):
            if 'enabled' in device.keys() and not strtobool(device.get('enabled')):
                continue
            cam_list[int(device.get('id'))] = device.get('name')

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

        use_saved_position = False
        try:
            use_saved_position = strtobool(settings.value("UseSavedPosition"))
        except:
            pass

        if not use_saved_position:
            settings.setValue("MainWindow/state", self.saveState())

        settings.setValue("AutoScreen", str(self.auto_screen_action.isChecked()))

    # ----------------------------------------------------------------------
    def save_widgets_layout(self):
        settings = QtCore.QSettings(APP_NAME)
        if self.saved_position_action.isChecked():
            settings.setValue("MainWindow/state", self.saveState())

        settings.setValue("UseSavedPosition", str(self.saved_position_action.isChecked()))

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

        use_saved_position = False
        try:
            use_saved_position = strtobool(settings.value("UseSavedPosition"))
        except:
            pass

        self.saved_position_action.setChecked(use_saved_position)
        self.position_on_exit_action.setChecked(not use_saved_position)

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

        widgets_menu = QtWidgets.QMenu('Widgets layout', self)
        self.menuBar().addMenu(widgets_menu)

        self.bg_position_on_exit = QtWidgets.QActionGroup(self)
        self.bg_position_on_exit.triggered.connect(self.save_widgets_layout)

        self.position_on_exit_action = QtWidgets.QAction('Use positions on exit', self)
        self.position_on_exit_action.setCheckable(True)
        self.bg_position_on_exit.addAction(self.position_on_exit_action)
        widgets_menu.addAction(self.position_on_exit_action)

        self.saved_position_action = QtWidgets.QAction('Save current position and use them', self)
        self.saved_position_action.setCheckable(True)
        self.bg_position_on_exit.addAction(self.saved_position_action)
        widgets_menu.addAction(self.saved_position_action)

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
    def _refresh_status(self):
        """
        """
        process = psutil.Process(os.getpid())
        mem = float(process.memory_info().rss) / (1024. * 1024.)
        cpu = psutil.cpu_percent()

        self._lb_resources_status.setText("| {:.2f}MB | CPU {} % |".format(mem,
                                                                           cpu))
        for widget in self.camera_widgets.values():
            id, state = widget.get_last_state()
            if id in self.camera_list:
                self.camera_dock_title[id].showTitle(not self.set_tab_style(self.camera_list[id], state))
                self.camera_dock_title[id].setRunning(state)
            else:
                print(f"Cannot find {id} in camera_list!")

    # ----------------------------------------------------------------------
    def set_tab_style(self, camera_name, state):
        tab_found = False
        for child in self.children():
            if isinstance(child, QtWidgets.QTabBar) and child.count():
                child.setStyleSheet("font-size: 12pt; font-weight: bold;")
                for ind in range(child.count()):
                    if child.tabText(ind) == camera_name:
                        tab_found = True
                        if state:
                            child.setTabTextColor(ind, QtGui.QColor('red'))
                        else:
                            child.setTabTextColor(ind, QtGui.QColor('black'))

        return tab_found


# ----------------------------------------------------------------------
class BatchLoader(QtCore.QThread):
    """
    separate QThread, that loads cameras
    """

    add_camera = QtCore.pyqtSignal(object, 'qint64')
    close_camera = QtCore.pyqtSignal(object, 'qint64')
    reload_camera = QtCore.pyqtSignal(object, 'qint64')

    loader_set_camera_status = QtCore.pyqtSignal(object, str)
    loader_set_progress = QtCore.pyqtSignal(float)

    set_done = QtCore.pyqtSignal()

    # ----------------------------------------------------------------------
    def __init__(self, main_window):
        super(BatchLoader, self).__init__()

        self.main_window = main_window

        self.jobs_to_be_done = []
        self.total_jobs = 0

        self.job_queue = Queue()
        self.job_id = 0

        self.stop_event = Event()
        self.is_done = Event()

        self.new_jobs = Event()

        self.workers = []
        for id in range(N_WORKERS):
            worker = CameraLoader(id, self.main_window, self.job_queue, self.stop_event)
            worker.add_camera.connect(lambda camera_id, job_id: self.add_camera.emit(camera_id, job_id))
            worker.close_camera.connect(lambda camera_id, job_id: self.close_camera.emit(camera_id, job_id))
            worker.reload_camera.connect(lambda camera_id, job_id: self.reload_camera.emit(camera_id, job_id))
            worker.loader_set_camera_status.connect(lambda camera, status:
                                                    self.loader_set_camera_status.emit(camera, status))

            self.workers.append(worker)
            worker.start()

    # ----------------------------------------------------------------------
    def wait_to_safe_close(self):
        self.stop_event.set()
        while np.any([worker.is_active() for worker in self.workers]) or not self.is_done.is_set():
            self.msleep(100)

        logger.debug("BatchLoader closed")

    # ----------------------------------------------------------------------
    def new_set_to_be_done(self, to_open, to_close, to_reload):
        logger.debug(f"New jobs set: open {to_open}, close {to_close}, reload {to_reload}")
        for camera_id in to_open:
            self.job_queue.put(("open", self.job_id, camera_id))
            self.jobs_to_be_done.append(self.job_id)
            self.job_id += 1

        for camera_id in to_close:
            self.job_queue.put(("close", self.job_id, camera_id))
            self.jobs_to_be_done.append(self.job_id)
            self.job_id += 1

        for camera_id in to_reload:
            self.job_queue.put(("reload", self.job_id, camera_id))
            self.jobs_to_be_done.append(self.job_id)
            self.job_id += 1

        self.total_jobs = len(self.jobs_to_be_done)
        self.new_jobs.set()

    # ----------------------------------------------------------------------
    def run(self):

        while not self.stop_event.is_set():
            if self.new_jobs.is_set():
                s_time = time.time()
                logger.debug("Processing new set")
                while len(self.jobs_to_be_done):
                    self.loader_set_progress.emit((self.total_jobs - len(self.jobs_to_be_done)) / self.total_jobs)
                    self.msleep(100)
                logger.debug(f"Jobs set done within {time.time() - s_time}")
                self.set_done.emit()
                self.new_jobs.clear()
            self.msleep(100)

        self.is_done.set()
        logger.debug(f"Butcher done")

    # ----------------------------------------------------------------------
    def job_done(self, job_id):
        logger.debug(f"Camera {job_id} done")
        if job_id in self.jobs_to_be_done:
            self.jobs_to_be_done.remove(job_id)
        else:
            print(f"Cannot find {job_id} in cameras_to_be_done")
        for worker in self.workers:
            worker.job_done(job_id)


# ----------------------------------------------------------------------
class CameraLoader(QtCore.QThread):
    add_camera = QtCore.pyqtSignal(object, 'qint64')
    close_camera = QtCore.pyqtSignal(object, 'qint64')
    reload_camera = QtCore.pyqtSignal(object, 'qint64')

    loader_set_camera_status = QtCore.pyqtSignal(object, str)

    # ----------------------------------------------------------------------
    def __init__(self, my_id, main_window, job_queue, stop_event):
        super(CameraLoader, self).__init__()
        self.job_queue = job_queue
        self.stop_event = stop_event
        self.camera_devices = main_window.camera_devices
        self.settings = main_window.settings
        self.my_id = my_id

        self.is_done = Event()

        self.done_jobs = []

    # ----------------------------------------------------------------------
    def run(self):
        while not self.stop_event.is_set():
            try:
                task, job_id, camera_id = self.job_queue.get(block=False)
                logger.debug(f"Loader {self.my_id} got task {task} for camera {camera_id}")
                if task == "open":
                    self.loader_set_camera_status.emit(camera_id, "opening...")
                    self.camera_devices[camera_id] = DataSource2D(self.settings, camera_id)
                    self.add_camera.emit(camera_id, job_id)
                if task == "close":
                    self.loader_set_camera_status.emit(camera_id, "closing...")
                    self.camera_devices[camera_id].close_camera()
                    self.close_camera.emit(camera_id, job_id)
                if task == "reload":
                    self.loader_set_camera_status.emit(camera_id, "reloading...")
                    self.camera_devices[camera_id].close_camera()
                    self.camera_devices[camera_id] = DataSource2D(self.settings, camera_id)
                    self.reload_camera.emit(camera_id, job_id)
                while job_id not in self.done_jobs:
                    self.msleep(100)
                if task == "open":
                    self.loader_set_camera_status.emit(camera_id, "opened.")
                if task == "close":
                    self.loader_set_camera_status.emit(camera_id, "closed.")
                if task == "reload":
                    self.loader_set_camera_status.emit(camera_id, "reloaded.")
            except Empty:
                self.msleep(100)

        logger.debug(f"Loader {self.my_id} no more tasks")
        self.is_done.set()

    # ----------------------------------------------------------------------
    def is_active(self):
        return not self.is_done.is_set()

    # ----------------------------------------------------------------------
    def job_done(self, camera_name):
        self.done_jobs.append(camera_name)
