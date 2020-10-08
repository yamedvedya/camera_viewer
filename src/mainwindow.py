#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de
# Last modified: 2017, November 20
# ----------------------------------------------------------------------

"""
"""

from __future__ import print_function

import getpass
import importlib
import logging
import os
import psutil
import socket
import subprocess
import fnmatch
import time

from functools import partial

from PyQt4 import QtCore, QtGui

import pyqtgraph as pg

from aboutdialog import AboutDialog
from utils.functions import (make_log_name,
                             parse_log_level)
from utils.xmlsettings import XmlSettings
from utils.guilogger import GuiLogger

from widgets.frameviewer import FrameViewer
from widgets.settingswidget import SettingsWidget
from widgets.logwidget import LogWidget

from roisrv.roiserver import RoiServer

from ui_vimbacam.MainWindow_ui import Ui_MainWindow
from ui_vimbacam import CameraSettingsWidget_ui

# ----------------------------------------------------------------------
class MainWindow(QtGui.QMainWindow):
    """
    """
    windowClosed = QtCore.Signal(str)

    APP_NAME = "P22 Camera Viewer"
    BEAMLINE_ID = "DESY_P22"

    LOG_PREVIEW = "gvim"
    STATUS_TICK = 2000              # [ms]

    # ----------------------------------------------------------------------
    def __init__(self, options):
        """
        """
        super(MainWindow, self).__init__()

        self.cfgPath = './config/'
        self.options = options
        self.generalSettings = XmlSettings(os.path.join('./config/', 'general.xml'))
        self.settings = XmlSettings(options.config)

        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")
        pg.setConfigOption("leftButtonPan", False)

        self.log, self._logFile, self._logDir, self._guiLogger = self._initLogger("cam_logger")

        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)

        self._initUi()

        self.loadUiSettings()

        self._statusTimer = QtCore.QTimer(self)
        self._statusTimer.timeout.connect(self._refreshStatusBar)
        self._statusTimer.start(self.STATUS_TICK)

        self._roiServer = []
        if self.generalSettings.option("roi_server", "enable").lower() == "true":
            try:
                self._roiServer = RoiServer(self.generalSettings.option("roi_server", "host"),
                                            self.generalSettings.option("roi_server", "port"))

                self._roiServer.settingWidget = self._settingsWidget
                self._roiServer.start()
            except Exception as err:
                self.log.exception(err)

        self._refreshTitle()
        self.log.info("Initialized successfully")

    # ----------------------------------------------------------------------
    def _initUi(self):
        """
        """
        self.setCentralWidget(None)

        self.setDockOptions(QtGui.QMainWindow.AnimatedDocks |
                            QtGui.QMainWindow.AllowNestedDocks |
                            QtGui.QMainWindow.AllowTabbedDocks)

        self._frameViewer, self._frameViewerDock = \
            self._addDock(FrameViewer, "Frame", QtCore.Qt.LeftDockWidgetArea,
                          self.generalSettings, self.settings, self)

        self._settingsWidget, self._settingsDock = \
            self._addDock(SettingsWidget, "General",
                          QtCore.Qt.RightDockWidgetArea,
                          self.settings, self)

        self._frameViewer.statusChanged.connect(self._displayCameraStatus)
        self._frameViewer.roiChanged.connect(self._settingsWidget.updateRoi)
        self._frameViewer.cursorMoved.connect(self._viewerCursorMoved)
        self._frameViewer.roiStats.connect(self._settingsWidget.updateStats)


        self._settingsWidget.markerChanged.connect(self._frameViewer.updateMarker)
        self._settingsWidget.roiChanged.connect(self._frameViewer.updateRoi)
        self._settingsWidget.roiMarkerSelected.connect(self._frameViewer.roiMarkerSelected)
        self._settingsWidget.enableAutoLevels.connect(self._frameViewer.enableAutoLevels)
        self._settingsWidget.levelsChanged.connect(self._frameViewer.levelsChanged)
        self._settingsWidget.colorMapChanged.connect(self._frameViewer.colorMapChanged)
        self._settingsWidget.set_dark_image.connect(self._frameViewer.set_dark_image)
        self._settingsWidget.remove_dark_image.connect(self._frameViewer.remove_dark_image)
        self._settingsWidget.image_size_changed.connect(self._frameViewer.move_image)
        self._settingsWidget._applySettings()
        self._initActions()

        self._toolBar = self._initToolBar()
        self.addToolBar(self._toolBar)
        self._initStatusBar()

    # ----------------------------------------------------------------------
    def _addDock(self, WidgetClass, label, location, *args, **kwargs):
        """
        """
        widget = WidgetClass(*args, **kwargs)

        dock = QtGui.QDockWidget(label)
        dock.setObjectName("{0}Dock".format("".join(label.split())))
        dock.setWidget(widget)

        self.addDockWidget(location, dock)
        self._ui.menuView.addAction(dock.toggleViewAction())

        return widget, dock

    # ----------------------------------------------------------------------
    def _displayCameraStatus(self, fps):
        """
        """
        self._lbFps.setText("{:.2f} FPS".format(fps))

            # more...


    # ----------------------------------------------------------------------
    def _viewerCursorMoved(self, x, y):
        """
        """
        self._lbCursorPos.setText("({:.2f}, {:.2f})".format(x, y))

    # ----------------------------------------------------------------------
    def _refreshTitle(self):
        """
        """
        deviceID = self.settings.option("device", "name")
        self.setWindowTitle("{} ({}@{})".format(deviceID,       #self.options.cameraID,
                                                getpass.getuser(),
                                                socket.gethostname()))

    # ----------------------------------------------------------------------
    def showSettingsDialog(self):
        """
        """
        self._frameViewer.stopLiveMode()
        print("Not yet implemented")

    # ----------------------------------------------------------------------
    def _showLogFile(self, logType="main"):
        """

        logType: main, stdout, stderr
        """
        camera = self.settings.option("device", "name")     #self.options.cameraID

        f = self._logFile
        if logType == "stdout":
            f = os.path.join("logs", "stdout_{}.log".format(camera))
        elif logType == "stderr":
            f = os.path.join("logs", "stderr_{}.log".format(camera))

        subprocess.Popen([self.LOG_PREVIEW, f])

    # ----------------------------------------------------------------------
    def showAbout(self):
        """
        """
        self._frameViewer.stopLiveMode()
        AboutDialog(self).exec_()

    # ----------------------------------------------------------------------
    def closeEvent(self, event):
        """
        """
        if self.cleanClose():
            event.accept()
        else:
            event.ignore()

    # ----------------------------------------------------------------------
    def cleanClose(self):
        """
        """
        self._frameViewer.stopLiveMode()

        if self._reallyQuit() == QtGui.QMessageBox.Yes:
            self.log.info("Closing the app...")

            self._frameViewer.close()
            if self._roiServer:
                self._roiServer.stop()
            self._settingsWidget.close()
            self._statusTimer.stop()

            self.saveUiSettings()

            QtGui.qApp.clipboard().clear()
            self.log.info("Closed properly")

            if not self.signalsBlocked():
                self.windowClosed.emit(self.APP_NAME)

            return True
        return False

    # ----------------------------------------------------------------------
    def quitProgram(self):
        """
        """
        if self.cleanClose():
            QtGui.qApp.quit()

    # ----------------------------------------------------------------------
    def _reallyQuit(self):
        """Make sure that the user wants to quit this program.
        """
        deviceID = self.settings.option("device", "name")
        appID = "{} viewer".format(deviceID)        #self.options.cameraID)
        return QtGui.QMessageBox.question(self, "Quit",
                                          "Do you really want to quit {}?".format(appID),
                                          QtGui.QMessageBox.Yes,
                                          QtGui.QMessageBox.No)

    # ----------------------------------------------------------------------
    def saveUiSettings(self):
        """Save basic GUI settings.
        """
        deviceID = self.settings.option("device", "name")
        
        settingsID = "VimbaCamera_{}".format(deviceID)      #:self.options.cameraID)
        settings = QtCore.QSettings(self.BEAMLINE_ID + "_CAM", settingsID)

        settings.setValue("CamWindow/geometry", self.saveGeometry())
        settings.setValue("CamWindow/state", self.saveState())

        self._frameViewer.saveUiSettings(settings)
        self._settingsWidget.saveUiSettings(settings)

    # ----------------------------------------------------------------------
    def loadUiSettings(self):
        """Load basic GUI settings.
        """
        deviceID = self.settings.option("device", "name")

        settingsID = "VimbaCamera_{}".format(deviceID)  #self.options.cameraID)
        settings = QtCore.QSettings(self.BEAMLINE_ID + "_CAM", settingsID)
        self._frameViewer.loadUiSettings(settings)
        self._settingsWidget.loadUiSettings(settings)

    # ----------------------------------------------------------------------
    def _initActions(self):
        """
        """
        self._ui.actionQuit.triggered.connect(self.quitProgram)
        self._ui.actionAbout.triggered.connect(self.showAbout)

        self._actionStartStop = QtGui.QAction(QtGui.QIcon(":/ico/play_16px.png"),
                                              "Start/Stop", self,
                                              triggered=self._frameViewer.startStopLiveMode)


        self._actionPrintImage = QtGui.QAction(QtGui.QIcon(":/ico/print.png"),
                                               "Print Image", self,
                                               triggered=self._frameViewer.printImage)
        self._actionPrintImage.setEnabled(False)

        self._actionCopyImage = QtGui.QAction(QtGui.QIcon(":/ico/copy.png"),
                                              "Copy to Clipboard", self,
                                              triggered=self._frameViewer.toClipboard)

        self._actionShowSettings = QtGui.QAction(QtGui.QIcon(":/ico/settings.png"),
                                                 "Settings", self,
                                                 triggered=self.showSettingsDialog)
        self._actionMoveScreen = QtGui.QAction(QtGui.QIcon(":/ico/crosshair-transparent-black.png"),
                                              "Screen In/Out", self,
                                              triggered=self._settingsWidget._moveScreen)

        self._frameViewer.deviceStarted.connect(lambda: self._actionStartStop.setIcon(
                                                    QtGui.QIcon(":/ico/stop.png")))
        self._frameViewer.deviceStopped.connect(lambda: self._actionStartStop.setIcon(
                                                    QtGui.QIcon(":/ico/play_16px.png")))

    # ----------------------------------------------------------------------
    def _makeSaveMenu(self, parent):
        """
        Args:
            parent (QWidget)
        """
        saveMenu = QtGui.QMenu(parent)

        self._saveImgAction = saveMenu.addAction("Image")
        #self._saveImgAction.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_H))
        self._saveImgAction.triggered.connect(self._frameViewer.saveToImage)

        self._saveAsciiAction = saveMenu.addAction("ASCII")
        self._saveAsciiAction.triggered.connect(partial(self._frameViewer.saveToFile,
                                                        fmt="csv"))

        self._saveNumpyAction = saveMenu.addAction("Numpy")
        self._saveNumpyAction.triggered.connect(partial(self._frameViewer.saveToFile,
                                                        fmt="npy"))
        return saveMenu

    # ----------------------------------------------------------------------
    def _makeLogPreviewMenu(self, parent):
        """
        Args:
            parent (QWidget)
        """
        logMenu = QtGui.QMenu(parent)

        self._mainLogAction = logMenu.addAction("Logfile")
        self._mainLogAction.triggered.connect(partial(self._showLogFile,
                                                      logType="main"))
        logMenu.addSeparator()

        self._stdoutLogAction = logMenu.addAction("Stdout")
        self._stdoutLogAction.triggered.connect(partial(self._showLogFile,
                                                        logType="stdout"))

        self._stderrLogAction = logMenu.addAction("Stderr")
        self._stderrLogAction.triggered.connect(partial(self._showLogFile,
                                                        logType="stderr"))
        return logMenu

    # ----------------------------------------------------------------------
    def _initToolBar(self):
        """
        """
        if hasattr(self, '_toolBar'):
            toolBar = self._toolBar
        else:
            toolBar = QtGui.QToolBar("Main toolbar", self)
            toolBar.setObjectName("VimbaCam_ToolBar")

        toolBar.addAction(self._actionStartStop)
        if self.settings.option("device", "tango_server"):
            toolBar.addAction(self._actionMoveScreen)
        toolBar.addSeparator()

            # image saving
        self._tbSaveScan = QtGui.QToolButton(self)
        self._tbSaveScan.setIcon(QtGui.QIcon(":/ico/save.png"))
        self._tbSaveScan.setToolTip("Save")

        self._saveMenu = self._makeSaveMenu(self._tbSaveScan)
        self._tbSaveScan.setMenu(self._saveMenu)
        self._tbSaveScan.setPopupMode(QtGui.QToolButton.InstantPopup)
        toolBar.addWidget(self._tbSaveScan)

        toolBar.addAction(self._actionPrintImage)
        toolBar.addAction(self._actionCopyImage)
        toolBar.addSeparator()

        toolBar.addAction(self._actionShowSettings)

        toolBar.addSeparator()
        self._cbCamSelector = QtGui.QComboBox()
        self.populateCamSelector()
        self._cbCamSelector.activated[str].connect(self.change_cam)
        toolBar.addWidget(self._cbCamSelector)
            # logs display
        self._tbShowLogs = QtGui.QToolButton(self)
        self._tbShowLogs.setIcon(QtGui.QIcon(":/ico/page.png"))
        self._tbShowLogs.setToolTip("Show logs")

        self._logShowMenu = self._makeLogPreviewMenu(self._tbShowLogs)
        self._tbShowLogs.setMenu(self._logShowMenu)
        self._tbShowLogs.setPopupMode(QtGui.QToolButton.InstantPopup)
        toolBar.addWidget(self._tbShowLogs)

        return toolBar

    # ----------------------------------------------------------------------
    def _initStatusBar(self):
        """
        """
        self._lbCursorPos = QtGui.QLabel("")

        processID = os.getpid()
        currentDir = os.getcwd()

        lbProcessID = QtGui.QLabel("PID {}".format(processID))
        lbProcessID.setStyleSheet("QLabel {color: #000066;}")
        lbCurrentDir = QtGui.QLabel("{}".format(currentDir))

            # resource usage
        process = psutil.Process(processID)
        mem = float(process.memory_info().rss) / (1024. * 1024.)
        cpu = process.cpu_percent()

        self._lbResourcesStatus = QtGui.QLabel("| {:.2f}MB | CPU {} % |".format(mem, cpu))

        self.statusBar().addPermanentWidget(self._lbCursorPos)
        self.statusBar().addPermanentWidget(lbProcessID)
        #self.statusBar().addPermanentWidget(lbCurrentDir)
        self.statusBar().addPermanentWidget(self._lbResourcesStatus)

        self._lbFps = QtGui.QLabel("FPS: -")
        self._lbFps.setMinimumWidth(70)
        self.statusBar().addPermanentWidget(self._lbFps)

    # ----------------------------------------------------------------------
    def _refreshStatusBar(self):
        """
        """
        process = psutil.Process(os.getpid())
        mem = float(process.memory_info().rss) / (1024. * 1024.)
        cpu = psutil.cpu_percent()

        self._lbResourcesStatus.setText("| {:.2f}MB | CPU {} % |".format(mem,
                                                                         cpu))

    # ----------------------------------------------------------------------
    def _initLogger(self, loggerName):
        """Initialize logging object

        Args:
            loggerName (str)
        """
        log = logging.getLogger(loggerName)

        level = parse_log_level("debug")
        log.setLevel(level)

        self.formatter = logging.Formatter("%(asctime)s %(module)s %(lineno)-6d %(levelname)-6s %(message)s")

            # logfile related to camera name
#        prefix = self.options.cameraID.replace(" ", "")
        
        prefix = "".join(self.settings.option("device", "name").split())
        logFile, logDir = make_log_name(prefix, "logs")

        fh = logging.FileHandler(logFile)
        fh.setFormatter(self.formatter)
        log.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(self.formatter)
        log.addHandler(ch)

        gh = GuiLogger()                        # ??? better name TODO
        gh.setFormatter(self.formatter)
        #log.addHandler(gh)

        print("{}\nIn case of problems look at: {}\n{}".format(
              "=" * 100, logFile, "=" * 100))

        return log, logFile, logDir, gh

    # ----------------------------------------------------------------------
    def change_logger(self):
        prefix = "".join(self.settings.option("device", "name").split())
        logFile, logDir = make_log_name(prefix, "logs")

        for hdlr in self.log.handlers:
            self.log.removeHandler(hdlr)
        for hdlr in self.log.handlers:
            self.log.removeHandler(hdlr)

        fh = logging.FileHandler(logFile)
        fh.setFormatter(self.formatter)
        self.log.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(self.formatter)
        self.log.addHandler(ch)

        gh = GuiLogger()
        gh.setFormatter(self.formatter)
        return logFile, logDir, gh

    # ----------------------------------------------------------------------
    def populateCamSelector(self):

        self.cam_configs = {}
        for f in os.listdir(self.cfgPath):
            if fnmatch.fnmatch(f,"camera_*.xml"):
                cam_name = XmlSettings(self.cfgPath+f).option("device", "name")
                self.cam_configs[cam_name] = f
        cam_list = self.cam_configs.keys()
        cam_list.sort()
        self._cbCamSelector.addItems(cam_list)
        self._cbCamSelector.setCurrentIndex(cam_list.index(self.settings.option("device", "name")))

    # ----------------------------------------------------------------------
    def change_cam(self, config):

        self.log.info("Changing camera...")

        self.saveUiSettings()
        self._frameViewer.close()
        time.sleep(0.5)
        self.removeDockWidget(self._frameViewerDock)
        self._settingsWidget.close()
        self.removeDockWidget(self._settingsDock)
        self._statusTimer.stop()
        for ac in self._toolBar.actions():
            self._toolBar.removeAction(ac)


        self.settings = XmlSettings(self.cfgPath+self.cam_configs[str(config)])
        self._logFile, self._logDir, self._guiLogger = self.change_logger()

        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)
        self._initUi()

        self.loadUiSettings()

        self._statusTimer = QtCore.QTimer(self)
        self._statusTimer.timeout.connect(self._refreshStatusBar)
        self._statusTimer.start(self.STATUS_TICK)

        self._refreshTitle()
        if self._roiServer:
            self._roiServer.settingWidget = self._settingsWidget
        self.log.info("Initialized new cam successfully")