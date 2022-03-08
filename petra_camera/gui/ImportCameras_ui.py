# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'uis/ImportCameras.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ImportCameras(object):
    def setupUi(self, ImportCameras):
        ImportCameras.setObjectName("ImportCameras")
        ImportCameras.resize(400, 249)
        self.verticalLayout = QtWidgets.QVBoxLayout(ImportCameras)
        self.verticalLayout.setObjectName("verticalLayout")
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(ImportCameras)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(ImportCameras)
        self.buttonBox.accepted.connect(ImportCameras.accept)
        self.buttonBox.rejected.connect(ImportCameras.reject)
        QtCore.QMetaObject.connectSlotsByName(ImportCameras)

    def retranslateUi(self, ImportCameras):
        _translate = QtCore.QCoreApplication.translate
        ImportCameras.setWindowTitle(_translate("ImportCameras", "Import cameras ..."))

