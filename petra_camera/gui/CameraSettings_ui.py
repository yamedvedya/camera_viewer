# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'uis/CameraSettings.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_CameraSettings(object):
    def setupUi(self, CameraSettings):
        CameraSettings.setObjectName("CameraSettings")
        CameraSettings.resize(557, 481)
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(CameraSettings)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(CameraSettings)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.cmb_camera_type = QtWidgets.QComboBox(CameraSettings)
        self.cmb_camera_type.setObjectName("cmb_camera_type")
        self.horizontalLayout.addWidget(self.cmb_camera_type)
        self.label_12 = QtWidgets.QLabel(CameraSettings)
        self.label_12.setObjectName("label_12")
        self.horizontalLayout.addWidget(self.label_12)
        self.le_name = QtWidgets.QLineEdit(CameraSettings)
        self.le_name.setObjectName("le_name")
        self.horizontalLayout.addWidget(self.le_name)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.cmd_delete = QtWidgets.QPushButton(CameraSettings)
        self.cmd_delete.setObjectName("cmd_delete")
        self.horizontalLayout.addWidget(self.cmd_delete)
        self.verticalLayout_5.addLayout(self.horizontalLayout)
        self.fr_tango = QtWidgets.QFrame(CameraSettings)
        self.fr_tango.setObjectName("fr_tango")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.fr_tango)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.label_2 = QtWidgets.QLabel(self.fr_tango)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_4.addWidget(self.label_2)
        self.le_tango_server = QtWidgets.QLineEdit(self.fr_tango)
        self.le_tango_server.setObjectName("le_tango_server")
        self.horizontalLayout_4.addWidget(self.le_tango_server)
        self.verticalLayout_5.addWidget(self.fr_tango)
        self.fr_roi = QtWidgets.QFrame(CameraSettings)
        self.fr_roi.setObjectName("fr_roi")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.fr_roi)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.label_3 = QtWidgets.QLabel(self.fr_roi)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_5.addWidget(self.label_3)
        self.le_roi_server = QtWidgets.QLineEdit(self.fr_roi)
        self.le_roi_server.setObjectName("le_roi_server")
        self.horizontalLayout_5.addWidget(self.le_roi_server)
        self.verticalLayout_5.addWidget(self.fr_roi)
        self.fr_settings = QtWidgets.QFrame(CameraSettings)
        self.fr_settings.setObjectName("fr_settings")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.fr_settings)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.label_4 = QtWidgets.QLabel(self.fr_settings)
        self.label_4.setObjectName("label_4")
        self.horizontalLayout_6.addWidget(self.label_4)
        self.le_settings_server = QtWidgets.QLineEdit(self.fr_settings)
        self.le_settings_server.setObjectName("le_settings_server")
        self.horizontalLayout_6.addWidget(self.le_settings_server)
        self.verticalLayout_5.addWidget(self.fr_settings)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_5 = QtWidgets.QLabel(CameraSettings)
        self.label_5.setObjectName("label_5")
        self.horizontalLayout_2.addWidget(self.label_5)
        self.cmb_motor_type = QtWidgets.QComboBox(CameraSettings)
        self.cmb_motor_type.setObjectName("cmb_motor_type")
        self.horizontalLayout_2.addWidget(self.cmb_motor_type)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.verticalLayout_5.addLayout(self.horizontalLayout_2)
        self.fr_motor = QtWidgets.QFrame(CameraSettings)
        self.fr_motor.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.fr_motor.setFrameShadow(QtWidgets.QFrame.Raised)
        self.fr_motor.setObjectName("fr_motor")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.fr_motor)
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_4.setSpacing(0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.fr_fsbt = QtWidgets.QFrame(self.fr_motor)
        self.fr_fsbt.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.fr_fsbt.setFrameShadow(QtWidgets.QFrame.Raised)
        self.fr_fsbt.setObjectName("fr_fsbt")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.fr_fsbt)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.label_7 = QtWidgets.QLabel(self.fr_fsbt)
        self.label_7.setObjectName("label_7")
        self.horizontalLayout_7.addWidget(self.label_7)
        self.le_fsbt_host = QtWidgets.QLineEdit(self.fr_fsbt)
        self.le_fsbt_host.setObjectName("le_fsbt_host")
        self.horizontalLayout_7.addWidget(self.le_fsbt_host)
        self.verticalLayout_2.addLayout(self.horizontalLayout_7)
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.label_8 = QtWidgets.QLabel(self.fr_fsbt)
        self.label_8.setObjectName("label_8")
        self.horizontalLayout_8.addWidget(self.label_8)
        self.le_fsbt_port = QtWidgets.QLineEdit(self.fr_fsbt)
        self.le_fsbt_port.setObjectName("le_fsbt_port")
        self.horizontalLayout_8.addWidget(self.le_fsbt_port)
        self.verticalLayout_2.addLayout(self.horizontalLayout_8)
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.label_9 = QtWidgets.QLabel(self.fr_fsbt)
        self.label_9.setObjectName("label_9")
        self.horizontalLayout_9.addWidget(self.label_9)
        self.le_fsbt_motor_name = QtWidgets.QLineEdit(self.fr_fsbt)
        self.le_fsbt_motor_name.setObjectName("le_fsbt_motor_name")
        self.horizontalLayout_9.addWidget(self.le_fsbt_motor_name)
        self.verticalLayout_2.addLayout(self.horizontalLayout_9)
        self.verticalLayout_4.addWidget(self.fr_fsbt)
        self.fr_acromag = QtWidgets.QFrame(self.fr_motor)
        self.fr_acromag.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.fr_acromag.setFrameShadow(QtWidgets.QFrame.Raised)
        self.fr_acromag.setObjectName("fr_acromag")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.fr_acromag)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.label_10 = QtWidgets.QLabel(self.fr_acromag)
        self.label_10.setObjectName("label_10")
        self.horizontalLayout_10.addWidget(self.label_10)
        self.le_acromag_server = QtWidgets.QLineEdit(self.fr_acromag)
        self.le_acromag_server.setObjectName("le_acromag_server")
        self.horizontalLayout_10.addWidget(self.le_acromag_server)
        self.verticalLayout_3.addLayout(self.horizontalLayout_10)
        self.horizontalLayout_11 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_11.setObjectName("horizontalLayout_11")
        self.label_11 = QtWidgets.QLabel(self.fr_acromag)
        self.label_11.setObjectName("label_11")
        self.horizontalLayout_11.addWidget(self.label_11)
        self.le_acromag_valve = QtWidgets.QLineEdit(self.fr_acromag)
        self.le_acromag_valve.setObjectName("le_acromag_valve")
        self.horizontalLayout_11.addWidget(self.le_acromag_valve)
        self.verticalLayout_3.addLayout(self.horizontalLayout_11)
        self.verticalLayout_4.addWidget(self.fr_acromag)
        self.verticalLayout_5.addWidget(self.fr_motor)
        self.groupBox = QtWidgets.QGroupBox(CameraSettings)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName("verticalLayout")
        self.chk_flip_v = QtWidgets.QCheckBox(self.groupBox)
        self.chk_flip_v.setObjectName("chk_flip_v")
        self.verticalLayout.addWidget(self.chk_flip_v)
        self.chk_flip_h = QtWidgets.QCheckBox(self.groupBox)
        self.chk_flip_h.setObjectName("chk_flip_h")
        self.verticalLayout.addWidget(self.chk_flip_h)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_6 = QtWidgets.QLabel(self.groupBox)
        self.label_6.setObjectName("label_6")
        self.horizontalLayout_3.addWidget(self.label_6)
        self.sp_rotate = QtWidgets.QSpinBox(self.groupBox)
        self.sp_rotate.setMaximum(3)
        self.sp_rotate.setObjectName("sp_rotate")
        self.horizontalLayout_3.addWidget(self.sp_rotate)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem2)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.verticalLayout_5.addWidget(self.groupBox)
        spacerItem3 = QtWidgets.QSpacerItem(20, 70, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_5.addItem(spacerItem3)

        self.retranslateUi(CameraSettings)
        QtCore.QMetaObject.connectSlotsByName(CameraSettings)

    def retranslateUi(self, CameraSettings):
        _translate = QtCore.QCoreApplication.translate
        CameraSettings.setWindowTitle(_translate("CameraSettings", "CameraSettings"))
        self.label.setText(_translate("CameraSettings", "Camera type"))
        self.label_12.setText(_translate("CameraSettings", "Name:"))
        self.cmd_delete.setText(_translate("CameraSettings", "Delete"))
        self.label_2.setText(_translate("CameraSettings", "Tango server"))
        self.label_3.setText(_translate("CameraSettings", "ROI server"))
        self.label_4.setText(_translate("CameraSettings", "Settings server"))
        self.label_5.setText(_translate("CameraSettings", "Screen motor type"))
        self.label_7.setText(_translate("CameraSettings", "FSBT server host"))
        self.label_8.setText(_translate("CameraSettings", "FSBT server post"))
        self.label_9.setText(_translate("CameraSettings", "FSBT motor name"))
        self.label_10.setText(_translate("CameraSettings", "Valve tango server"))
        self.label_11.setText(_translate("CameraSettings", "Valve channel"))
        self.groupBox.setTitle(_translate("CameraSettings", "Picture settings"))
        self.chk_flip_v.setText(_translate("CameraSettings", "Flip vertical"))
        self.chk_flip_h.setText(_translate("CameraSettings", "Flip horizontal"))
        self.label_6.setText(_translate("CameraSettings", "Rotate in 90 deg step"))
