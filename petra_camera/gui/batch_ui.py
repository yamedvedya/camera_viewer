# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'uis/batch.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_batch(object):
    def setupUi(self, batch):
        batch.setObjectName("batch")
        batch.resize(400, 100)
        self.verticalLayout = QtWidgets.QVBoxLayout(batch)
        self.verticalLayout.setObjectName("verticalLayout")
        self.lb_camera_name = QtWidgets.QLabel(batch)
        self.lb_camera_name.setObjectName("lb_camera_name")
        self.verticalLayout.addWidget(self.lb_camera_name)
        self.pb_progress = QtWidgets.QProgressBar(batch)
        self.pb_progress.setProperty("value", 0)
        self.pb_progress.setObjectName("pb_progress")
        self.verticalLayout.addWidget(self.pb_progress)
        self.but_box = QtWidgets.QDialogButtonBox(batch)
        self.but_box.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.but_box.setStandardButtons(QtWidgets.QDialogButtonBox.Abort)
        self.but_box.setObjectName("but_box")
        self.verticalLayout.addWidget(self.but_box)

        self.retranslateUi(batch)
        QtCore.QMetaObject.connectSlotsByName(batch)

    def retranslateUi(self, batch):
        _translate = QtCore.QCoreApplication.translate
        batch.setWindowTitle(_translate("batch", "Batch processing"))
        self.lb_camera_name.setText(_translate("batch", "Open camera..."))

