#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de
# Last modified: 2017, December 13
# ----------------------------------------------------------------------

"""
"""

import logging
import subprocess

import socket
import errno, time
import json
from StringIO import StringIO

try:
    import PyTango
except ImportError:
    pass

from src.utils.errors import report_error

from PyQt4 import QtCore, QtGui

from src.ui_vimbacam.SettingsWidget_ui import Ui_SettingsWidget


# ----------------------------------------------------------------------
class SettingsWidget(QtGui.QWidget):
    """
    """
    markerChanged = QtCore.Signal(int, int, int, bool)
    roiChanged = QtCore.Signal(int, int, int, int, float, bool)
    roiStats = QtCore.Signal(int, int, float, float, int)
    roiMarkerSelected = QtCore.Signal(str)

    colorMapChanged = QtCore.Signal(str)
    levelsChanged = QtCore.Signal(float, float)
    enableAutoLevels = QtCore.Signal(bool)
    set_dark_image = QtCore.Signal()
    remove_dark_image = QtCore.Signal()
    image_size_changed = QtCore.Signal(float, float, float, float)

    PARAMS_EDITOR = "atkpanel"
    SYNC_TICK = 4000  # [ms]
    SOCKET_TIMEOUT = 5
    DATA_BUFFER_SIZE = 2 ** 22
    NUM_MARKERS = 2

    # ----------------------------------------------------------------------
    def __init__(self, settings, parent):
        """
        """
        super(SettingsWidget, self).__init__(parent)
        self.settings = settings
        self.log = logging.getLogger("cam_logger")

        self._deviceID = settings.option("device", "name")

        self._proxyType = settings.option("device", "proxy")

        self._ui = Ui_SettingsWidget()
        self._ui.setupUi(self)
        self._roiMarker = ''
        self._ui.tbAllParams.clicked.connect(self._editAllParams)
        self._ui.sbExposureTime.editingFinished.connect(lambda: self._settingsChanged('Exposure'))
        self._ui.sbGain.editingFinished.connect(lambda: self._settingsChanged('Gain'))
        self._ui.sbViewX.editingFinished.connect(lambda: self._settingsChanged('X'))
        self._ui.sbViewY.editingFinished.connect(lambda: self._settingsChanged('Y'))
        self._ui.sbViewW.editingFinished.connect(lambda: self._settingsChanged('W'))
        self._ui.sbViewH.editingFinished.connect(lambda: self._settingsChanged('H'))

        for marker in range(self.NUM_MARKERS):
            getattr(self._ui, "sbMarkerX_{}".format(marker)).valueChanged.connect(
                lambda value, x=marker: self._markerChanged(x))
            getattr(self._ui, "sbMarkerY_{}".format(marker)).valueChanged.connect(
                lambda value, x=marker: self._markerChanged(x))
            getattr(self._ui, "chbShowMarker_{}".format(marker)).stateChanged.connect(
                lambda state, x=marker: self._markerChanged(x))
        self.marker2ectrl = [None for _ in range(self.NUM_MARKERS)]

        self._ui.chkAutoLevels.stateChanged.connect(self._autoLevelsChanged)
        self._ui.sbMinLevel.valueChanged.connect(self._levelsChanged)
        self._ui.sbMaxLevel.valueChanged.connect(self._levelsChanged)
        self._ui.cbColorMap.currentIndexChanged.connect(self._colorMapChanged)
        self._ui.sbRoiX.valueChanged.connect(self._roiChanged)
        self._ui.sbRoiY.valueChanged.connect(self._roiChanged)
        self._ui.sbRoiWidth.valueChanged.connect(self._roiChanged)
        self._ui.sbRoiHeight.valueChanged.connect(self._roiChanged)
        self._ui.sbThreshold.valueChanged.connect(self._roiChanged)
        self._ui.chbShowRoi.stateChanged.connect(self._roiChanged)
        self._ui.pbInOut.clicked.connect(self._moveScreen)
        self._ui.bgRoiMarker.buttonClicked.connect(self._roiMarkerChanged)
        self._ui.tbDarkImage.clicked.connect(self.set_dark_image)
        self._ui.tbDarkImageDelete.clicked.connect(self.remove_dark_image)

        if self._proxyType == 'TangoTineProxy':
            self._settingsServer = settings.option("device", "settings_server")
            self._deviceProxy = PyTango.DeviceProxy(str(self._settingsServer))
            self._exposureName = "ExposureValue.Set"
            self._gainName = "GainValue.Set"
            att_conf_exposure = self._deviceProxy.get_attribute_config('ExposureValue.Set')
            att_conf_gain = self._deviceProxy.get_attribute_config('GainValue.Set')
            exposure_max = self._deviceProxy.read_attribute('ExposureValue.Max')
            exposure_min = self._deviceProxy.read_attribute('ExposureValue.Min')
            gain_max = self._deviceProxy.read_attribute('GainValue.Max')
            gain_min = self._deviceProxy.read_attribute('GainValue.Min')
            att_conf_exposure.max_value = str(exposure_max.value)
            att_conf_exposure.min_value = str(exposure_min.value)
            att_conf_gain.max_value = str(gain_max.value)
            att_conf_gain.min_value = str(gain_min.value)
            self._deviceProxy.set_attribute_config(att_conf_exposure)
            self._deviceProxy.set_attribute_config(att_conf_gain)

        elif self._proxyType == 'VimbaProxy':
            self._tangoServer = settings.option("device", "tango_server")
            self._deviceProxy = PyTango.DeviceProxy(str(self._tangoServer))
            self._exposureName = "ExposureTimeAbs"
            self._viewX_name = "OffsetX"
            self._viewY_name = "OffsetY"
            self._viewH_name = "Height"
            self._viewHmax_name = "HeightMax"
            self._viewW_name = "Width"
            self._viewWmax_name = "WidthMax"
            self.hMax = self._deviceProxy.read_attribute(self._viewHmax_name).value
            self.wMax = self._deviceProxy.read_attribute(self._viewWmax_name).value
            # self._deviceProxy.write_attribute(self._viewX_name, 0)
            # self._deviceProxy.write_attribute(self._viewY_name, 0)
            # self._deviceProxy.write_attribute(self._viewW_name, self.wMax)
            # self._deviceProxy.write_attribute(self._viewH_name, self.hMax)

            self._gainName = str(self._deviceProxy.get_property('GainFeatureName')['GainFeatureName'][0])
            self._high_depth = settings.option("device", "high_depth")

            if self._high_depth:
                self._ui.sbMaxLevel.setMaximum(2 ** 12)
                self._ui.sbMinLevel.setMaximum(2 ** 12)
            else:
                self._ui.sbMaxLevel.setMaximum(2 ** 8)
                self._ui.sbMinLevel.setMaximum(2 ** 8)

        try:
            if settings.option("motor", "type") == 'none':
                self._ui.pbInOut.setEnabled(False)
            elif settings.option("motor", "type") == 'Acromag':
                self._ui.pbInOut.setEnabled(True)
                self._motorType = 'Acromag'
                self._valveTangoServer = settings.option("motor", "valve_tango_server")
                self._valveChannel = int(settings.option("motor", "valve_channel"))
                self._valveDeviceProxy = PyTango.DeviceProxy(self._valveTangoServer)

            elif settings.option("motor", "type") == 'FSBT':
                self._ui.pbInOut.setEnabled(True)
                self._motorType = 'FSBT'
                self._fsbtServerHost = settings.option("motor", "host")
                self._fsbtServerPort = int(settings.option("motor", "port"))
                self._motorName = settings.option("motor", "name")
        except:
            self._ui.pbInOut.setEnabled(False)

        self.vflip = self.settings.option("flip", "vertical") == "True"
        self.hflip = self.settings.option("flip", "horizontal") == "True"

        self._tangoMutex = QtCore.QMutex()
        self._reloadSettings()

        # keep in sync with TANGO
        self._syncTimer = QtCore.QTimer(self)
        self._syncTimer.timeout.connect(self._reloadSettings)
        # self._syncTimer.start(self.SYNC_TICK)


    # ----------------------------------------------------------------------
    def updateLevels(self, min, max, map):
        """
        """
        self._blockSignals(True)
        self._ui.sbMinLevel.setValue(min)
        self._ui.sbMaxLevel.setValue(max)
        # self._ui.cbColorMap.setItemText(map)

        index = self._ui.cbColorMap.findText(map, QtCore.Qt.MatchFixedString)
        if index >= 0:
            self._ui.cbColorMap.setCurrentIndex(index)

        self.levelsChanged.emit(min, max)
        self.colorMapChanged.emit(map)
        self._blockSignals(False)

    # ----------------------------------------------------------------------
    def updateMarker(self, num, x, y):
        """
        """
        self._blockSignals(True)

        getattr(self._ui, 'sbMarkerX_{:d}'.format(num)).setValue(x)
        getattr(self._ui, 'sbMarkerY_{:d}'.format(num)).setValue(y)

        self._blockSignals(False)

    # ----------------------------------------------------------------------
    def updateRoi(self, x, y, w, h, threshold):
        """
        """
        self._blockSignals(True)

        self._ui.sbRoiX.setValue(x)
        self._ui.sbRoiY.setValue(y)
        self._ui.sbRoiWidth.setValue(w)
        self._ui.sbRoiHeight.setValue(h)
        self._ui.sbThreshold.setValue(threshold)

        self.x = x
        self.y = y

        self._blockSignals(False)

    # CS
    # ----------------------------------------------------------------------
    def updateStats(self, Extrema, CoM, CoMval, FWHM, Sum):
        """Stats changed     """
        self._ui.leMaxVal.setText('{:2.2f}'.format(Extrema[1]))
        self._ui.leMinVal.setText('{:2.2f}'.format(Extrema[0]))
        self._ui.leMinX.setText(str(Extrema[2][0] + self.x))
        self._ui.leMinY.setText(str(Extrema[2][1] + self.y))
        self._ui.leMaxX.setText(str(Extrema[3][0] + self.x))
        self._ui.leMaxY.setText(str(Extrema[3][1] + self.y))
        self._ui.leComX.setText(str("{:10.2f}".format(CoM[0])))
        self._ui.leComY.setText(str("{:10.2f}".format(CoM[1])))
        self._ui.leComVal.setText(str(CoMval))
        self._ui.leFwhmX.setText(str(FWHM[0]))
        self._ui.leFwhmY.setText(str(FWHM[1]))
        self.roiCoM = [CoM[0], CoM[1], CoMval]
        self.sum = Sum

        self._ui.leXcorr.setText(str("{:10.2f}".format(FWHM[0] * 1.0787)))
        self._ui.leYcorr.setText(str("{:10.2f}".format(FWHM[1] * 0.7029)))

        self._ui.leSum.setText(str(Sum))

    # ----------------------------------------------------------------------
    def _markerChanged(self, num):
        """
        """
        x = getattr(self._ui, 'sbMarkerX_{:d}'.format(num)).value()
        y = getattr(self._ui, 'sbMarkerY_{:d}'.format(num)).value()
        visible = getattr(self._ui, 'chbShowMarker_{:d}'.format(num)).isChecked()

        getattr(self._ui, 'sbMarkerX_{:d}'.format(num)).setEnabled(visible)
        getattr(self._ui, 'sbMarkerY_{:d}'.format(num)).setEnabled(visible)

        self.marker2ectrl = (x, y, visible)

        self.markerChanged.emit(num, x, y, visible)

    # ----------------------------------------------------------------------
    def _roiMarkerChanged(self):
        """
        """
        if self._ui.chbShowMax.isChecked():
            if self._roiMarker != 'max':
                self._ui.chbShowMin.setChecked(False)
                self._ui.chbShowCom.setChecked(False)
                self._roiMarker = 'max'
        else:
            if self._roiMarker == 'max':
                self._roiMarker = ''

        if self._ui.chbShowMin.isChecked():
            if self._roiMarker != 'min':
                self._ui.chbShowMax.setChecked(False)
                self._ui.chbShowCom.setChecked(False)
                self._roiMarker = 'min'
        else:
            if self._roiMarker == 'min':
                self._roiMarker = ''

        if self._ui.chbShowCom.isChecked():
            if self._roiMarker != 'com':
                self._ui.chbShowMax.setChecked(False)
                self._ui.chbShowMin.setChecked(False)
                self._roiMarker = 'com'
        else:
            if self._roiMarker == 'com':
                self._roiMarker = ''

        visible = 'none'
        if self._ui.chbShowMax.isChecked():
            visible = 'max'
        elif self._ui.chbShowMin.isChecked():
            visible = 'min'
        elif self._ui.chbShowCom.isChecked():
            visible = 'com'
        self.roiMarkerSelected.emit(visible)

    # ----------------------------------------------------------------------
    def _roiChanged(self):
        """
        """
        x = self._ui.sbRoiX.value()
        y = self._ui.sbRoiY.value()
        w = self._ui.sbRoiWidth.value()
        h = self._ui.sbRoiHeight.value()
        threshold = self._ui.sbThreshold.value()

        visible = self._ui.chbShowRoi.isChecked()
        self._ui.sbRoiX.setEnabled(visible)
        self._ui.sbRoiY.setEnabled(visible)
        self._ui.sbRoiWidth.setEnabled(visible)
        self._ui.sbRoiHeight.setEnabled(visible)

        self.roi2ectrl = (x, y, w, h, threshold, visible)
        self.roiChanged.emit(x, y, w, h, threshold, visible)

    # ----------------------------------------------------------------------
    def _settingsChanged(self, type):
        """
        """
        with QtCore.QMutexLocker(self._tangoMutex):
            self._applySettings()

        # self._reloadSettings()

    #        self._ui.tbApply.setEnabled(True)

    # ----------------------------------------------------------------------
    def _reloadSettings(self):
        """From the TANGO db.
        """
        self._blockSignals(True)

        try:
            with QtCore.QMutexLocker(self._tangoMutex):
                try:
                    exposureTime = self._deviceProxy.read_attribute(self._exposureName).value
                except:
                    exposureTime = self._deviceProxy.read_attribute('ExposureValue.Default').value
                    self._deviceProxy.write_attribute(self._exposureName, exposureTime)
                try:
                    gain = self._deviceProxy.read_attribute(self._gainName).value
                except:
                    gain = self._deviceProxy.read_attribute('GainValue.Default').value
                    self._deviceProxy.write_attribute(self._gainName, gain)
                try:
                    self.hMax = self._deviceProxy.read_attribute(self._viewHmax_name).value
                    self.wMax = self._deviceProxy.read_attribute(self._viewWmax_name).value
                    self.viewX = self._deviceProxy.read_attribute(self._viewX_name).value
                    self.viewY = self._deviceProxy.read_attribute(self._viewY_name).value
                    self.viewW = self._deviceProxy.read_attribute(self._viewW_name).value
                    self.viewH = self._deviceProxy.read_attribute(self._viewH_name).value
                    if self.hflip:
                        viewX = self.wMax - self.viewW - self.viewX
                    else:
                        viewX = self.viewX
                    if self.vflip:
                        viewY = self.hMax - self.viewH - self.viewY
                    else:
                        viewY = self.viewY
                    # self._deviceProxy.write_attribute(self._viewX_name, 0)
                    # self._deviceProxy.write_attribute(self._viewY_name, 0)
                    # self._deviceProxy.write_attribute(self._viewW_name, self.wMax)
                    # self._deviceProxy.write_attribute(self._viewH_name, self.hMax)
                    self._ui.sbViewX.setValue(viewX)
                    self._ui.sbViewX.setMaximum(self.wMax - self.viewW)
                    self._ui.sbViewY.setValue(viewY)
                    self._ui.sbViewY.setMaximum(self.hMax - self.viewH)
                    self._ui.sbViewW.setValue(self.viewW)
                    self._ui.sbViewW.setMaximum(self.wMax - viewX)
                    self._ui.sbViewH.setValue(self.viewH)
                    self._ui.sbViewH.setMaximum(self.hMax - viewY)
                except:
                    self._ui.sbViewX.setDisabled(True)
                    self._ui.sbViewY.setDisabled(True)
                    self._ui.sbViewW.setDisabled(True)
                    self._ui.sbViewH.setDisabled(True)

                self._ui.sbExposureTime.setValue(int(exposureTime))
                self._ui.sbGain.setValue(gain)

                if self._proxyType == 'VimbaProxy':
                    try:
                        fps = self._deviceProxy.read_attribute("AcquisitionFrameRateAbs").value
                    except:
                        fps = 1.0
                else:
                    fps = 1.0

                self._ui.lbFps.setText("FPS limit: {:.2f}".format(fps))

        except Exception as err:
            report_error(err, self.log, self)

        self._blockSignals(False)

    # ----------------------------------------------------------------------
    def _applySettings(self):
        """Save camera's settings to the TANGO db.
        """
        # stop acq if it's running? TODO
        try:
            exposureTime = min(max(float(self._ui.sbExposureTime.value()), 50), 1e6)
            gain = min(max(float(self._ui.sbGain.value()), 0), 22)

            self._deviceProxy.write_attribute(self._exposureName, exposureTime)
            self._deviceProxy.write_attribute(self._gainName, gain)

            # reload fps...
            #            fps = camera.read_attribute("AcquisitionFrameRateAbs").value
            if self._proxyType == 'VimbaProxy':
                try:
                    fps = self._deviceProxy.read_attribute("AcquisitionFrameRateLimit").value
                except:
                    fps = 1.0

                viewX = min(max(self._ui.sbViewX.value(), 0), self.wMax)
                viewY = min(max(self._ui.sbViewY.value(), 0), self.hMax)  # make sure tha offsetX + width < Wmax
                viewW = min(max(self._ui.sbViewW.value(), 1), self.wMax)  # can only be changed in increments of 4
                viewH = min(max(self._ui.sbViewH.value(), 1), self.hMax)
                self._ui.sbViewX.setMaximum(self.wMax - viewW)
                self._ui.sbViewY.setMaximum(self.hMax - viewH)
                self._ui.sbViewW.setMaximum(self.wMax - viewX)
                self._ui.sbViewH.setMaximum(self.hMax - viewY)
                self.image_size_changed.emit(viewX, viewY, viewW, viewH)

                if self.hflip:
                    viewX = self.wMax - viewW - viewX
                if self.vflip:
                    viewY = self.hMax - viewH - viewY
                print(viewW, viewH, viewX, viewY)
                self._deviceProxy.write_attribute(self._viewW_name, viewW)
                self._deviceProxy.write_attribute(self._viewH_name, viewH)
                self._deviceProxy.write_attribute(self._viewX_name, viewX)
                self._deviceProxy.write_attribute(self._viewY_name, viewY)
            else:
                fps = 2
            self._ui.lbFps.setText("{:.2f}".format(fps))
            self.log.debug("Settings saved, exposure time: {}, gain: {}".format(exposureTime, gain))

        except Exception as err:
            if str(err).find('The value was not valid'):
                QtGui.QMessageBox.warning(self, "Achtung!", "The value is not valid!",
                                          QtGui.QMessageBox.Ok)

                return
            else:
                report_error(err, self.log, self)

    # ----------------------------------------------------------------------
    def _editAllParams(self):
        """
        """
        server = self._tangoServer
        server = "/" + "/".join(server.split("/")[1:])

        self.log.info("Edit all params, server: {}".format(server))

        subprocess.Popen([self.PARAMS_EDITOR, server])

    # ----------------------------------------------------------------------
    def saveUiSettings(self, settings):
        """
        Args:
            (QSettings)
        """
        levelMin = self._ui.sbMinLevel.value()
        levelMax = self._ui.sbMaxLevel.value()
        colorMap = str(self._ui.cbColorMap.currentText()).lower()
        settings.setValue("SettingsWidget/levelMin", levelMin)
        settings.setValue("SettingsWidget/levelMax", levelMax)
        settings.setValue("SettingsWidget/colorMap", colorMap)
        settings.setValue("SettingsWidget/autoLevelsSet", self._ui.chkAutoLevels.isChecked())

        for marker in range(self.NUM_MARKERS):
            markerX = getattr(self._ui, "sbMarkerX_{:d}".format(marker)).value()
            markerY = getattr(self._ui, "sbMarkerY_{:d}".format(marker)).value()
            self.log.info("Marker position: {}, {}".format(markerX, markerY))

            settings.setValue("SettingsWidget/markerX_{:d}".format(marker), markerX)
            settings.setValue("SettingsWidget/markerY_{:d}".format(marker), markerY)
            settings.setValue("SettingsWidget/markerVisible_{:d}".format(marker),
                              getattr(self._ui, "chbShowMarker_{:d}".format(marker)).isChecked())

        roiX = self._ui.sbRoiX.value()
        roiY = self._ui.sbRoiY.value()
        roiW = self._ui.sbRoiWidth.value()
        roiH = self._ui.sbRoiHeight.value()
        roiThres = self._ui.sbThreshold.value()
        self.log.info("ROI position: {}, {}, size: {}, {}".format(roiX, roiY,
                                                                  roiW, roiH))
        # save ROI position and state
        settings.setValue("SettingsWidget/roiX", roiX)
        settings.setValue("SettingsWidget/roiY", roiY)
        settings.setValue("SettingsWidget/roiWidth", roiW)
        settings.setValue("SettingsWidget/roiHeight", roiH)
        settings.setValue("SettingsWidget/roiThres", roiThres)
        settings.setValue("SettingsWidget/roiVisible",
                          self._ui.chbShowRoi.isChecked())

        settings.setValue("SettingsWidget/geometry", self.saveGeometry())
        # settings.setValue("SettingsWidget/state", self.saveState())

    # ----------------------------------------------------------------------
    def loadUiSettings(self, settings):
        """
        Args:
            (QSettings)
        """
        min, _ = settings.value("SettingsWidget/levelMin").toInt()
        max, _ = settings.value("SettingsWidget/levelMax").toInt()
        map = settings.value("SettingsWidget/colorMap").toString()
        autoLevels = settings.value("SettingsWidget/autoLevelsSet").toBool()
        self._ui.chkAutoLevels.setChecked(autoLevels)
        self.updateLevels(min, max, map)

        x, _ = settings.value("SettingsWidget/roiX").toInt()
        y, _ = settings.value("SettingsWidget/roiY").toInt()
        w, _ = settings.value("SettingsWidget/roiWidth").toInt()
        h, _ = settings.value("SettingsWidget/roiHeight").toInt()
        threshold, _ = settings.value("SettingsWidget/roiThres").toFloat()
        self.updateRoi(x, y, w, h, threshold)

        visible = settings.value("SettingsWidget/roiVisible").toBool()
        self._ui.chbShowRoi.setChecked(visible)

        self._ui.sbRoiX.setEnabled(visible)
        self._ui.sbRoiY.setEnabled(visible)
        self._ui.sbRoiWidth.setEnabled(visible)
        self._ui.sbRoiHeight.setEnabled(visible)

        for marker in range(self.NUM_MARKERS):
            try:
                x, _ = settings.value("SettingsWidget/markerX_{:d}".format(marker)).toInt()
                y, _ = settings.value("SettingsWidget/markerY_{:d}".format(marker)).toInt()
                visible = settings.value("SettingsWidget/markerVisible_{:d}".format(marker)).toBool()
            except:
                x = 0
                y = 0
                visible = False

            self.updateMarker(marker, x, y)
            getattr(self._ui, "sbMarkerX_{:d}".format(marker)).setEnabled(visible)
            getattr(self._ui, "sbMarkerY_{:d}".format(marker)).setEnabled(visible)
            getattr(self._ui, "chbShowMarker_{:d}".format(marker)).setChecked(visible)

        self.restoreGeometry(settings.value("SettingsWidget/geometry").toByteArray())

    # ----------------------------------------------------------------------
    def _blockSignals(self, flag):
        """
        """
        self._ui.sbRoiX.blockSignals(flag)
        self._ui.sbRoiY.blockSignals(flag)
        self._ui.sbRoiWidth.blockSignals(flag)
        self._ui.sbRoiHeight.blockSignals(flag)
        self._ui.chbShowRoi.blockSignals(flag)

        for marker in range(self.NUM_MARKERS):
            getattr(self._ui, "sbMarkerX_{:d}".format(marker)).blockSignals(flag)
            getattr(self._ui, "sbMarkerY_{:d}".format(marker)).blockSignals(flag)
            getattr(self._ui, "chbShowMarker_{:d}".format(marker)).blockSignals(flag)

        self._ui.sbExposureTime.blockSignals(flag)
        self._ui.sbGain.blockSignals(flag)

    # ----------------------------------------------------------------------

    def _autoLevelsChanged(self):
        if self._ui.chkAutoLevels.isChecked():
            self._ui.sbMinLevel.setEnabled(False)
            self._ui.sbMaxLevel.setEnabled(False)
            self.enableAutoLevels.emit(True)
        else:
            self._ui.sbMinLevel.setEnabled(True)
            self._ui.sbMaxLevel.setEnabled(True)
            self.enableAutoLevels.emit(False)
            self._levelsChanged()

    # ----------------------------------------------------------------------

    def _levelsChanged(self):
        min = self._ui.sbMinLevel.value()
        max = self._ui.sbMaxLevel.value()
        self.levelsChanged.emit(min, max)

    # ----------------------------------------------------------------------

    def _colorMapChanged(self):
        selectedMap = str(self._ui.cbColorMap.currentText()).lower()
        self.colorMapChanged.emit(selectedMap)

    # ----------------------------------------------------------------------

    def close(self):
        if hasattr(self, '_roiServer'):
            self._roiServer.stop()
        super(SettingsWidget, self).close()

    # ----------------------------------------------------------------------
    def _moveScreen(self):
        if self._motorType == 'Acromag':
            self._currentPos = list('{0:04b}'.format(int(self._valveDeviceProxy.read_attribute("Register0").value)))
            self._newPos = self.intToBin(self._valveChannel)

            if self._currentPos[3 - self._valveChannel] == "1":
                self._ui.pbInOut.setText('In')
                self._currentPos[3 - self._valveChannel] = '0'
            else:
                self._ui.pbInOut.setText('Out')
                self._currentPos[3 - self._valveChannel] = '1'
            new_state = int("".join(self._currentPos), 2)

            self._valveDeviceProxy.write_attribute("Register0", new_state)

        elif self._motorType == 'FSBT':
            try:
                FSBTServer = self.getConnectionToFSBT()
                if FSBTServer:
                    status = self.sendCommandToFSBT(FSBTServer, 'status ' + self._motorName)

                    if status[1][self._motorName] == 'in':
                        result = self.sendCommandToFSBT(FSBTServer, 'out {:s}'.format(self._motorName))
                    else:
                        result = self.sendCommandToFSBT(FSBTServer, 'in {:s}'.format(self._motorName))

                    FSBTServer.close()
            except Exception as err:
                pass

    # ----------------------------------------------------------------------
    def getConnectionToFSBT(self):

        FSBTSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        FSBTSocket.settimeout(self.SOCKET_TIMEOUT)

        startTimeout = time.time()
        timeOut = False
        is_connected = False
        while not timeOut and not is_connected:
            err = FSBTSocket.connect_ex((self._fsbtServerHost, self._fsbtServerPort))
            if err == 0 or err == errno.EISCONN:
                is_connected = True
            if time.time() - startTimeout > self.SOCKET_TIMEOUT:
                timeOut = True

        if is_connected:
            return FSBTSocket
        else:
            return None

    # ----------------------------------------------------------------------
    def sendCommandToFSBT(self, FSBTSocket, command):

        FSBTSocket.sendall(str(command))

        startTimeout = time.time()
        timeOut = False
        gotAnswer = False
        ans = ''
        while not timeOut and not gotAnswer:
            try:
                ans = FSBTSocket.recv(self.DATA_BUFFER_SIZE)
                gotAnswer = True
            except socket.error as err:
                if err.errno != 11:
                    timeOut = True
                if time.time() - startTimeout > self.SOCKET_TIMEOUT:
                    timeOut = True
        if not timeOut:
            return json.load(StringIO(ans))
        else:
            raise RuntimeError("The FSBT server does not responsd")

    # ----------------------------------------------------------------------
    def intToBin(self, val):
        b = '{0:04b}'.format(val)
        l = [0] * 4

        for i in range(4):
            l[i] = int(b[i], 2)

        return l

    # ----------------------------------------------------------------------
    def getCameraSettings(self):
        return (self._ui.sbExposureTime.value(), self._ui.sbGain.value())

    # ----------------------------------------------------------------------
    def setCameraSettings(self, settings):

        values = json.loads(settings)
        self._ui.sbExposureTime.setValue(values[0])
        self._ui.sbGain.setValue(values[1])
        self._applySettings()

        return ""

    # ----------------------------------------------------------------------
    def getValue(self, value):
        try:
            return getattr(self, value)
        except:
            return 0
