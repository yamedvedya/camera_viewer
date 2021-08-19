# Created by matveyev at 19.08.2021

import logging

from functools import partial
from PyQt5 import QtCore, QtWidgets, QtGui

from src.utils.errors import report_error

from src.widgets.base_widget import APP_NAME
from src.widgets.frame_viewer import FrameViewer
from src.widgets.settings_widget import SettingsWidget
from src.widgets.marker_roi import MarkersROIsWidget
from src.widgets.peak_search_widget import PeakSearchWidget

from src.devices.datasource2d import DataSource2D
from src.gui.CameraWidget_ui import Ui_CameraWindow
from src.utils.functions import add_dock


# ----------------------------------------------------------------------
class CameraWidget(QtWidgets.QMainWindow):

    # ----------------------------------------------------------------------
    def __init__(self, parent, settings, my_name):
        """
        """
        super(CameraWidget, self).__init__(parent)

        self.settings = settings
        self.camera_name = my_name

        self._log = logging.getLogger("cam_logger")

        self.camera_device = DataSource2D(self)
        if not self.camera_device.new_device_proxy(self.camera_name, parent.auto_screen_action.isChecked()):
            raise RuntimeError('Cannot start camera')

        self._ui = Ui_CameraWindow()
        self._ui.setupUi(self)
        self._init_ui()

        self.camera_device.newFrame.connect(self._frame_viewer.refresh_view)
        self.camera_device.gotError.connect(lambda err_msg: report_error(err_msg, self.log, self, True))

        self._parent = parent

        self._refresh_view_timer = QtCore.QTimer(self)
        self._refresh_view_timer.timeout.connect(self._refresh_view)
        self._refresh_view_timer.start()

    # ----------------------------------------------------------------------
    def _refresh_view(self):

        state = self.camera_device.is_running()
        if state is None:
            self._actionStartStop.setIcon(QtGui.QIcon(":/ico/play_16px.png"))
            self._actionStartStop.setEnabled(False)
        elif state:
            self._actionStartStop.setIcon(QtGui.QIcon(":/ico/stop.png"))
            self._actionStartStop.setEnabled(True)
        else:
            self._actionStartStop.setIcon(QtGui.QIcon(":/ico/play_16px.png"))
            self._actionStartStop.setEnabled(True)

        self._settings_widget.refresh_view()
        self._markerroi_widget.refresh_view()
        self._markerroi_widget.refresh_view()
        self._frame_viewer.refresh_image()

    # ----------------------------------------------------------------------
    def clean_close(self):
        self._log.info(f"Closing {self.camera_name}...")

        self._settings_widget.close()
        self._frame_viewer.close()

        self.camera_device.close_camera(self._parent.auto_screen_action.isChecked())

        self._frame_viewer.save_ui_settings(self.camera_name)
        self._settings_widget.save_ui_settings(self.camera_name)
        self._markerroi_widget.save_ui_settings(self.camera_name)
        self._peak_search_widget.save_ui_settings(self.camera_name)

        self._save_ui_settings()

        self._log.info(f"{self.camera_name} closed.")

    # ----------------------------------------------------------------------
    def _display_camera_status(self, fps):
        """
        """
        self._lb_fps.setText("{:.2f} FPS".format(fps))

    # ----------------------------------------------------------------------
    def _viewer_cursor_moved(self, x, y):
        """
        """
        self._lb_cursor_pos.setText("({:.2f}, {:.2f})".format(x, y))

    # ----------------------------------------------------------------------
    # -------------------- UI initialization -------------------------------
    # ----------------------------------------------------------------------
    def _init_ui(self):
        """
        """
        self.setCentralWidget(None)

        self.setDockOptions(QtWidgets.QMainWindow.AnimatedDocks |
                            QtWidgets.QMainWindow.AllowNestedDocks |
                            QtWidgets.QMainWindow.AllowTabbedDocks)

        self._frame_viewer, self._frameViewer_dock = \
            add_dock(self, self._ui.menu_widgets, FrameViewer, "Frame", self)

        self._settings_widget, self._settings_dock = \
            add_dock(self, self._ui.menu_widgets, SettingsWidget, "Settings", self)

        self._markerroi_widget, self._markerroi_dock = \
            add_dock(self, self._ui.menu_widgets, MarkersROIsWidget, "Markers/ROIs", self)

        self._peak_search_widget, self._peak_search_dock = \
            add_dock(self, self._ui.menu_widgets, PeakSearchWidget, "Peak Search", self)

        self._frame_viewer.load_ui_settings(self.camera_name)
        self._settings_widget.load_ui_settings(self.camera_name)
        self._markerroi_widget.load_ui_settings(self.camera_name)
        self._peak_search_widget.load_ui_settings(self.camera_name)

        self._frame_viewer.status_changed.connect(self._display_camera_status)
        self._frame_viewer.cursor_moved.connect(self._viewer_cursor_moved)
        self._frame_viewer.refresh_numbers.connect(self._settings_widget.refresh_view)

        self._settings_widget.refresh_image.connect(self._frame_viewer.refresh_image)
        self._markerroi_widget.refresh_image.connect(self._frame_viewer.refresh_image)
        self._peak_search_widget.refresh_image.connect(self._frame_viewer.refresh_image)

        self._init_actions()

        self._toolBar = self._init_tool_bar()
        self.addToolBar(self._toolBar)

        self._init_status_bar()

    # ----------------------------------------------------------------------
    def _init_actions(self):
        """
        """
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
    def _init_tool_bar(self):
        """
        """
        if hasattr(self, '_toolBar'):
            toolBar = self._toolBar
        else:
            toolBar = QtWidgets.QToolBar("Main toolbar", self)
            toolBar.setObjectName("VimbaCam_ToolBar")

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

        return toolBar

    # ----------------------------------------------------------------------
    def _init_status_bar(self):

        self._lb_cursor_pos = QtWidgets.QLabel("")

        self._lb_fps = QtWidgets.QLabel("FPS: -")
        self._lb_fps.setMinimumWidth(70)

        self.statusBar().addPermanentWidget(self._lb_cursor_pos)
        self.statusBar().addPermanentWidget(self._lb_fps)

    # ----------------------------------------------------------------------
    def _save_ui_settings(self):
        """Save basic GUI settings.
        """
        settings = QtCore.QSettings(APP_NAME)

        settings.setValue(f"{self.camera_name}/geometry", self.saveGeometry())
        settings.setValue(f"{self.camera_name}/state", self.saveState())

    # ----------------------------------------------------------------------
    def load_ui_settings(self):
        """Load basic GUI settings.
        """
        settings = QtCore.QSettings(APP_NAME)

        try:
            self.restoreGeometry(settings.value(f"{self.camera_name}/geometry"))
        except:
            pass

        try:
            self.restoreState(settings.value(f"{self.camera_name}/state"))
        except:
            pass
