# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/Marker.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Marker(object):
    def setupUi(self, Marker):
        Marker.setObjectName("Marker")
        Marker.resize(283, 41)
        self.horizontalLayout = QtWidgets.QHBoxLayout(Marker)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_23 = QtWidgets.QLabel(Marker)
        self.label_23.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_23.setObjectName("label_23")
        self.horizontalLayout.addWidget(self.label_23)
        self.sb_x = QtWidgets.QSpinBox(Marker)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sb_x.sizePolicy().hasHeightForWidth())
        self.sb_x.setSizePolicy(sizePolicy)
        self.sb_x.setMaximum(99999)
        self.sb_x.setObjectName("sb_x")
        self.horizontalLayout.addWidget(self.sb_x)
        self.label_24 = QtWidgets.QLabel(Marker)
        self.label_24.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_24.setObjectName("label_24")
        self.horizontalLayout.addWidget(self.label_24)
        self.sb_y = QtWidgets.QSpinBox(Marker)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sb_y.sizePolicy().hasHeightForWidth())
        self.sb_y.setSizePolicy(sizePolicy)
        self.sb_y.setMaximum(99999)
        self.sb_y.setObjectName("sb_y")
        self.horizontalLayout.addWidget(self.sb_y)
        self.but_delete = QtWidgets.QPushButton(Marker)
        self.but_delete.setObjectName("but_delete")
        self.horizontalLayout.addWidget(self.but_delete)

        self.retranslateUi(Marker)
        QtCore.QMetaObject.connectSlotsByName(Marker)

    def retranslateUi(self, Marker):
        _translate = QtCore.QCoreApplication.translate
        Marker.setWindowTitle(_translate("Marker", "Form"))
        self.label_23.setText(_translate("Marker", "X:"))
        self.label_24.setText(_translate("Marker", "Y:"))
        self.but_delete.setText(_translate("Marker", "Delete"))
