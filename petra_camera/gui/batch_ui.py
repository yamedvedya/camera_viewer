# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'uis/batch.ui'
#
# Created by: PyQt5 UI code generator 5.15.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_batch(object):
    def setupUi(self, batch):
        batch.setObjectName("batch")
        batch.resize(398, 144)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(batch.sizePolicy().hasHeightForWidth())
        batch.setSizePolicy(sizePolicy)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(batch)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.layout_names = QtWidgets.QVBoxLayout()
        self.layout_names.setObjectName("layout_names")
        self.horizontalLayout.addLayout(self.layout_names)
        self.layout_status = QtWidgets.QVBoxLayout()
        self.layout_status.setObjectName("layout_status")
        self.horizontalLayout.addLayout(self.layout_status)
        self.horizontalLayout.setStretch(0, 1)
        self.verticalLayout_3.addLayout(self.horizontalLayout)
        self.pb_progress = QtWidgets.QProgressBar(batch)
        self.pb_progress.setMinimumSize(QtCore.QSize(380, 0))
        self.pb_progress.setProperty("value", 0)
        self.pb_progress.setObjectName("pb_progress")
        self.verticalLayout_3.addWidget(self.pb_progress)

        self.retranslateUi(batch)
        QtCore.QMetaObject.connectSlotsByName(batch)

    def retranslateUi(self, batch):
        _translate = QtCore.QCoreApplication.translate
        batch.setWindowTitle(_translate("batch", "Batch processing"))
