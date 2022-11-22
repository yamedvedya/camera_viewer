# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'uis/EmptyCameraWidget.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_EmptyCameraWindow(object):
    def setupUi(self, EmptyCameraWindow):
        EmptyCameraWindow.setObjectName("EmptyCameraWindow")
        EmptyCameraWindow.resize(852, 523)
        self.centralwidget = QtWidgets.QWidget(EmptyCameraWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.lb_error = QtWidgets.QLabel(self.centralwidget)
        self.lb_error.setAlignment(QtCore.Qt.AlignCenter)
        self.lb_error.setObjectName("lb_error")
        self.verticalLayout.addWidget(self.lb_error)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.cmd_reinit_camera = QtWidgets.QPushButton(self.centralwidget)
        self.cmd_reinit_camera.setObjectName("cmd_reinit_camera")
        self.horizontalLayout.addWidget(self.cmd_reinit_camera)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem2)
        self.verticalLayout.addLayout(self.horizontalLayout)
        spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem3)
        EmptyCameraWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(EmptyCameraWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 852, 23))
        self.menubar.setObjectName("menubar")
        EmptyCameraWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(EmptyCameraWindow)
        self.statusbar.setSizeGripEnabled(False)
        self.statusbar.setObjectName("statusbar")
        EmptyCameraWindow.setStatusBar(self.statusbar)
        self.quit_action = QtWidgets.QAction(EmptyCameraWindow)
        self.quit_action.setObjectName("quit_action")
        self.actionAbout = QtWidgets.QAction(EmptyCameraWindow)
        self.actionAbout.setObjectName("actionAbout")

        self.retranslateUi(EmptyCameraWindow)
        QtCore.QMetaObject.connectSlotsByName(EmptyCameraWindow)

    def retranslateUi(self, EmptyCameraWindow):
        _translate = QtCore.QCoreApplication.translate
        EmptyCameraWindow.setWindowTitle(_translate("EmptyCameraWindow", "FailedCameraWindow"))
        self.label_2.setText(_translate("EmptyCameraWindow", "Camera initialization error:"))
        self.lb_error.setText(_translate("EmptyCameraWindow", "TextLabel"))
        self.cmd_reinit_camera.setText(_translate("EmptyCameraWindow", "Re-initialize camera"))
        self.quit_action.setText(_translate("EmptyCameraWindow", "Quit..."))
        self.quit_action.setShortcut(_translate("EmptyCameraWindow", "Ctrl+Q"))
        self.actionAbout.setText(_translate("EmptyCameraWindow", "About..."))

import petra_camera.gui.icons_rc
