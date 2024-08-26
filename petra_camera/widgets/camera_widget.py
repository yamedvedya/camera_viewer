# Created by matveyev at 19.08.2021
"""
  Widget for individual camera.
  Has 4 dockable widgets: Frame viewer, Settings, ROI & Marker, PeakSearch.
  Also has his own datasource instance

"""

import logging

try:
    import skimage
    peak_search = True
except:
    peak_search = False

from functools import partial
from PyQt5 import QtCore, QtWidgets, QtGui

from petra_camera.utils.errors import report_error

from petra_camera.constants import APP_NAME
from petra_camera.widgets.frame_viewer import FrameViewer
from petra_camera.widgets.settings_widget import SettingsWidget
from petra_camera.widgets.marker_roi import MarkersROIsWidget
from petra_camera.widgets.peak_search_widget import PeakSearchWidget
from petra_camera.widgets.position_control import PositionControl

from petra_camera.gui.CameraWidget_ui import Ui_CameraWindow

logger = logging.getLogger(APP_NAME)


# ----------------------------------------------------------------------
class CameraWidget(QtWidgets.QMainWindow):

    REFRESH_TANGO_SETTINGS_PERIOD = 5000 # how often we update settings with Tango
    REFRESH_ICONS_PERIOD = 500 # how often we update settings with Tango

    # ----------------------------------------------------------------------
    def __init__(self, parent, dock, camera):
        """
        """
        super(CameraWidget, self).__init__(parent)

        self.settings = parent.settings

        self.my_dock = dock

        self.camera_id = camera.camera_id
        self._last_state = None
        self._parent = parent

        self.hist_lock = QtCore.QMutex()

        self.camera_device = camera

        self._ui = Ui_CameraWindow()
        self._ui.setupUi(self)
        self._init_ui()

        self._refresh_view_timer = QtCore.QTimer(self)
        self._refresh_view_timer.timeout.connect(self._refresh_view)
        self._refresh_view_timer.start(self.REFRESH_TANGO_SETTINGS_PERIOD)

        self._refresh_run_stop_timer = QtCore.QTimer(self)
        self._refresh_run_stop_timer.timeout.connect(self._refresh_icons)
        self._refresh_run_stop_timer.start(self.REFRESH_ICONS_PERIOD)

    # ----------------------------------------------------------------------
    def _start_stop_live_mode(self):
        """

        :return: None
        """

        try:
            self._frame_viewer.start_stop_live_mode(self._parent.auto_screen_action.isChecked())
        except Exception as err:
            self._log.exception(err)
            report_error(err)

    # ----------------------------------------------------------------------
    def clean_close(self):
        """

        :return: None
        """
        logger.info(f"Closing {self.camera_id}...")

        self._settings_widget.close()
        if self._position_control_widget is not None:
            self._position_control_widget.close()

        self._frame_viewer.save_ui_settings(self.camera_id)
        self._settings_widget.save_ui_settings(self.camera_id)
        self._markerroi_widget.save_ui_settings(self.camera_id)
        if self._peak_search_widget is not None:
            self._peak_search_widget.save_ui_settings(self.camera_id)

        if self._position_control_widget is not None:
            self._position_control_widget.save_ui_settings(self.camera_id)

        self._save_ui_settings()

        logger.info(f"{self.camera_id} closed.")

    # ----------------------------------------------------------------------
    def _refresh_icons(self):
        try:
            self._last_state = self.camera_device.is_running()
            if self._last_state is None:
                self._action_start_stop.setIcon(QtGui.QIcon(":/ico/play_16px.png"))
                self._action_start_stop.setEnabled(False)
            elif self._last_state:
                self._action_start_stop.setIcon(QtGui.QIcon(":/ico/stop.png"))
                self._action_start_stop.setEnabled(True)
            else:
                self._action_start_stop.setIcon(QtGui.QIcon(":/ico/play_16px.png"))
                self._action_start_stop.setEnabled(True)
        except Exception as err:
            logger.exception(f"Exception: camera state: {err}")

        try:
            position = self.camera_device.motor_position()

            self._move_motor_action.setVisible(position is not None)
            if position is None:
                self._move_motor_label.setText('')
            else:
                self._move_motor_action.setIcon(QtGui.QIcon(":/ico/screen_out.png")
                                                if position else QtGui.QIcon(":/ico/screen_in.png"))

                self._move_motor_label.setText('Move screen OUT' if position else 'Move screen IN')
                self._move_motor_action.setText('Move screen OUT' if position else 'Move screen IN')
                self._move_motor_action.setToolTip('Move screen OUT' if position else 'Move screen IN')
        except Exception as err:
            logger.exception(f"Exception: motor state: {err}")

    # ----------------------------------------------------------------------
    def get_last_state(self):
        return self.camera_id, self._last_state

    # ----------------------------------------------------------------------
    def _refresh_view(self):
        """

        :return: None
        """

        if self._settings_widget.isVisible():
            self._settings_widget.refresh_view()

    # ----------------------------------------------------------------------
    def _display_fps(self, fps):
        """

        :param fps: value, int
        :return: None
        """
        self._lb_fps.setText("{:.2f} FPS".format(fps))

    # ----------------------------------------------------------------------
    def _viewer_cursor_moved(self, x, y):
        """

        :param x: mouse coordinate
        :param y: mouse coordinate
        :return: None
        """
        self._lb_cursor_pos.setText("({:.2f}, {:.2f})".format(x, y))

    # ----------------------------------------------------------------------
    # -------------------- UI initialization -------------------------------
    # ----------------------------------------------------------------------
    def _init_ui(self):

        self.tool_bar = QtWidgets.QToolBar("Main toolbar", self)
        self.tool_bar.setObjectName("CameraViewer_ToolBar")

        self._action_start_stop = QtWidgets.QAction(self)
        self._action_start_stop.setIcon(QtGui.QIcon(":/ico/play_16px.png"))
        self._action_start_stop.setText("Start/Stop")

        self.tool_bar.addAction(self._action_start_stop)
        self.tool_bar.addSeparator()

        # image saving
        self._tbSaveScan = QtWidgets.QToolButton(self)
        self._tbSaveScan.setIcon(QtGui.QIcon(":/ico/save.png"))
        self._tbSaveScan.setToolTip("Save")

        self._saveMenu = self._make_save_menu(self._tbSaveScan)
        self._tbSaveScan.setMenu(self._saveMenu)
        self._tbSaveScan.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.tool_bar.addWidget(self._tbSaveScan)

        self._action_print_image = QtWidgets.QAction(self)
        self._action_print_image.setIcon(QtGui.QIcon(":/ico/print.png"))
        self._action_print_image.setText("Print Image")
        self._action_print_image.setEnabled(False)
        self.tool_bar.addAction(self._action_print_image)

        self._action_copy_image = QtWidgets.QAction(self)
        self._action_copy_image.setIcon(QtGui.QIcon(":/ico/copy.png"))
        self._action_copy_image.setText("Copy to Clipboard")
        self.tool_bar.addAction(self._action_copy_image)

        self.tool_bar.addSeparator()
        self._move_motor_label = QtWidgets.QLabel('Move screen IN:')
        self.tool_bar.addWidget(self._move_motor_label)
        self._move_motor_action = QtWidgets.QAction(self)
        self._move_motor_action.setIcon(QtGui.QIcon(":/ico/screen_in.png"))
        self._move_motor_action.setText("Move screen IN")
        self.tool_bar.addAction(self._move_motor_action)

        self.tool_bar.addSeparator()
        self.tool_bar.addWidget(QtWidgets.QLabel('Widgets:'))

        self.addToolBar(self.tool_bar)

        self._lb_cursor_pos = QtWidgets.QLabel("")

        self._lb_fps = QtWidgets.QLabel("FPS: -")
        self._lb_fps.setMinimumWidth(70)

        self.statusBar().addPermanentWidget(self._lb_cursor_pos)
        self.statusBar().addPermanentWidget(self._lb_fps)

        self.setCentralWidget(None)

        self.setDockOptions(QtWidgets.QMainWindow.AnimatedDocks |
                            QtWidgets.QMainWindow.AllowNestedDocks |
                            QtWidgets.QMainWindow.AllowTabbedDocks)

        self._frame_viewer, self._frameViewer_dock = \
            self._add_dock(FrameViewer, "Frame", self)

        self._settings_widget, self._settings_dock = \
            self._add_dock(SettingsWidget, "Settings", self)

        self._markerroi_widget, self._markerroi_dock = \
            self._add_dock(MarkersROIsWidget, "Markers/ROIs", self)

        if peak_search:
            self._peak_search_widget, self._peak_search_dock = \
                self._add_dock(PeakSearchWidget, "Peak Search", self)
        else:
            self._peak_search_widget, self._peak_search_dock = None, None

        if self.camera_device.get_camera_type() == 'AXISCamera':
            self._position_control_widget, self._position_control_dock = \
                self._add_dock(PositionControl, "Position Control", self)
        else:
            self._position_control_widget, self._position_control_dock = None, None

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred);
        self.tool_bar.addWidget(spacer)

        # Dock button
        dock_button = QtWidgets.QToolButton()
        dock_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_TitleBarShadeButton))
        dock_button.clicked.connect(self.toggleDocked)
        self.tool_bar.addWidget(dock_button)

        # Close button
        close_button = QtWidgets.QToolButton()
        close_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_TitleBarCloseButton))
        close_button.clicked.connect(self.closeDockWidget)
        self.tool_bar.addWidget(close_button)

        # after all widgets are loaded we restore the user layout
        self._frame_viewer.load_ui_settings(self.camera_id)
        self._settings_widget.load_ui_settings(self.camera_id)
        self._markerroi_widget.load_ui_settings(self.camera_id)
        if self._peak_search_widget is not None:
            self._peak_search_widget.load_ui_settings(self.camera_id)

        if self._position_control_widget is not None:
            self._position_control_widget.load_ui_settings(self.camera_id)

        # link between picture and histogram
        self._settings_widget.set_frame_to_hist(self._frame_viewer.get_image_view())
        self._frame_viewer.set_hist(self._settings_widget.get_hist())

        self._frame_viewer.new_fps.connect(self._display_fps)
        self._frame_viewer.cursor_moved.connect(self._viewer_cursor_moved)

        self.camera_device.new_frame.connect(self._frame_viewer.new_frame)

        self.camera_device.update_roi_statistics.connect(self._markerroi_widget.update_roi_statistics)
        self.camera_device.update_roi_statistics.connect(self._frame_viewer.repaint_roi)

        self.camera_device.update_peak_search.connect(self._frame_viewer.repaint_peak_search)

        self.camera_device.got_error.connect(lambda err_msg: report_error(err_msg, self, True))

        self._markerroi_widget.add_remove_marker.connect(self._frame_viewer.add_remove_marker)
        self._markerroi_widget.repaint_marker.connect(self._frame_viewer.repaint_marker)

        self._markerroi_widget.add_remove_roi.connect(self._frame_viewer.add_remove_roi)
        self._markerroi_widget.repaint_roi.connect(self._frame_viewer.repaint_roi)

        self._action_start_stop.triggered.connect(self._start_stop_live_mode)
        self._action_print_image.triggered.connect(self._frame_viewer.print_image)
        self._action_copy_image.triggered.connect(self._frame_viewer.to_clipboard)

        self._save_img_action.triggered.connect(self._frame_viewer.save_to_image)
        self._save_ascii_action.triggered.connect(partial(self._frame_viewer.save_to_file, fmt="csv"))
        self._save_numpy_action.triggered.connect(partial(self._frame_viewer.save_to_file, fmt="npy"))

        self._move_motor_action.triggered.connect(lambda: self.camera_device.move_motor())

    # ----------------------------------------------------------------------
    def toggleDocked(self):
        if self.my_dock.isFloating():
            self.my_dock.setFloating(False)
        else:
            self.my_dock.setFloating(True)

    # ----------------------------------------------------------------------
    def closeDockWidget(self):
        self.my_dock.close()

    # ----------------------------------------------------------------------
    def block_hist_signals(self):
        return self._settings_widget.block_hist_signals()

    # ----------------------------------------------------------------------
    def _add_dock(self, WidgetClass, label, *args, **kwargs):

        widget = WidgetClass(*args, **kwargs)

        dock = QtWidgets.QDockWidget(label)
        dock.setObjectName("{0}Dock".format("".join(label.split())))
        dock.setStyleSheet("""QDockWidget {font-size: 11pt; font-weight: normal}""")
        dock.setWidget(widget)

        if WidgetClass == FrameViewer:
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)
        else:
            children = [child for child in self.findChildren(QtWidgets.QDockWidget)
                        if not isinstance(child.widget(), FrameViewer)]

            if children:
                self.tabifyDockWidget(children[-1], dock)
            else:
                self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

        self.tool_bar.addAction(dock.toggleViewAction())

        return widget, dock

    # ----------------------------------------------------------------------
    def _make_save_menu(self, parent):
        """
        Args:
            parent (QWidget)
        """
        saveMenu = QtWidgets.QMenu(parent)

        self._save_img_action = saveMenu.addAction("Image")

        self._save_ascii_action = saveMenu.addAction("ASCII")

        self._save_numpy_action = saveMenu.addAction("Numpy")

        return saveMenu

    # ----------------------------------------------------------------------
    def _save_ui_settings(self):
        """Save basic GUI settings.
        """
        settings = QtCore.QSettings(APP_NAME)

        settings.setValue(f"{self.camera_id}/geometry", self.saveGeometry())
        settings.setValue(f"{self.camera_id}/state", self.saveState())

    # ----------------------------------------------------------------------
    def load_ui_settings(self):
        """Load basic GUI settings.
        """
        settings = QtCore.QSettings(APP_NAME)

        try:
            self.restoreGeometry(settings.value(f"{self.camera_id}/geometry"))
        except:
            pass

        try:
            self.restoreState(settings.value(f"{self.camera_id}/state"))
        except:
            pass


# ----------------------------------------------------------------------
class CustomTitleBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(CustomTitleBar, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout()

        self.titleLabel = QtWidgets.QLabel("Your Custom Title")
        layout.addWidget(self.titleLabel)

        self.setLayout(layout)

    # ----------------------------------------------------------------------
    def setTitle(self, new_title):
        self.titleLabel.setText(new_title)

    # ----------------------------------------------------------------------
    def showTitle(self, state):
        if state:
            self.titleLabel.show()
        else:
            self.titleLabel.hide()

    # ----------------------------------------------------------------------
    def setRunning(self, running):
        if running:
            self.titleLabel.setStyleSheet("QLabel {font-size: 12pt; font-weight: bold; color: red};")
        else:
            self.titleLabel.setStyleSheet("QLabel {font-size: 12pt; font-weight: bold; color: black};")