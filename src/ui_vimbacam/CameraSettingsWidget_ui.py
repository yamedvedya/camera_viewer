# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/CameraSettingsWidget.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_CameraSettingsWidget(object):
    def setupUi(self, CameraSettingsWidget):
        CameraSettingsWidget.setObjectName("CameraSettingsWidget")
        CameraSettingsWidget.resize(398, 279)
        self.verticalLayout = QtWidgets.QVBoxLayout(CameraSettingsWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.sbExposureTime = QtWidgets.QSpinBox(CameraSettingsWidget)
        self.sbExposureTime.setEnabled(True)
        self.sbExposureTime.setMinimumSize(QtCore.QSize(120, 0))
        self.sbExposureTime.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.sbExposureTime.setMaximum(999999999)
        self.sbExposureTime.setObjectName("sbExposureTime")
        self.gridLayout.addWidget(self.sbExposureTime, 0, 1, 1, 1)
        self.label_5 = QtWidgets.QLabel(CameraSettingsWidget)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 2, 0, 1, 1)
        self.label_3 = QtWidgets.QLabel(CameraSettingsWidget)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 0, 0, 1, 1)
        self.sbGain = QtWidgets.QSpinBox(CameraSettingsWidget)
        self.sbGain.setEnabled(True)
        self.sbGain.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.sbGain.setMaximum(999999999)
        self.sbGain.setObjectName("sbGain")
        self.gridLayout.addWidget(self.sbGain, 2, 1, 1, 1)
        self.lbFps = QtWidgets.QLabel(CameraSettingsWidget)
        self.lbFps.setObjectName("lbFps")
        self.gridLayout.addWidget(self.lbFps, 1, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.tbAllParams = QtWidgets.QToolButton(CameraSettingsWidget)
        self.tbAllParams.setEnabled(True)
        self.tbAllParams.setObjectName("tbAllParams")
        self.horizontalLayout.addWidget(self.tbAllParams)
        self.verticalLayout.addLayout(self.horizontalLayout)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)

        self.retranslateUi(CameraSettingsWidget)
        QtCore.QMetaObject.connectSlotsByName(CameraSettingsWidget)

    def retranslateUi(self, CameraSettingsWidget):
        _translate = QtCore.QCoreApplication.translate
        CameraSettingsWidget.setWindowTitle(_translate("CameraSettingsWidget", "Form"))
        self.label_5.setText(_translate("CameraSettingsWidget", "Gain:"))
        self.label_3.setText(_translate("CameraSettingsWidget", "Exposure time:"))
        self.lbFps.setText(_translate("CameraSettingsWidget", "<FPS>"))
        self.tbAllParams.setToolTip(_translate("CameraSettingsWidget", "More Settings"))
        self.tbAllParams.setText(_translate("CameraSettingsWidget", "..."))
