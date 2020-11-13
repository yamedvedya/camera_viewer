# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/FrameViewer.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_FrameViewer(object):
    def setupUi(self, FrameViewer):
        FrameViewer.setObjectName("FrameViewer")
        FrameViewer.resize(945, 707)
        self.horizontalLayout = QtWidgets.QHBoxLayout(FrameViewer)
        self.horizontalLayout.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.splitter_x = QtWidgets.QSplitter(FrameViewer)
        self.splitter_x.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_x.setObjectName("splitter_x")
        self.splitter_y1 = QtWidgets.QSplitter(self.splitter_x)
        self.splitter_y1.setOrientation(QtCore.Qt.Vertical)
        self.splitter_y1.setObjectName("splitter_y1")
        self.imageView = ImageViewNoKeyboard(self.splitter_y1)
        self.imageView.setObjectName("imageView")
        self.wiProfileX = ProjectionWidget(self.splitter_y1)
        self.wiProfileX.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.wiProfileX.setObjectName("wiProfileX")
        self.splitter_y2 = QtWidgets.QSplitter(self.splitter_x)
        self.splitter_y2.setOrientation(QtCore.Qt.Vertical)
        self.splitter_y2.setObjectName("splitter_y2")
        self.wiProfileY = ProjectionWidget(self.splitter_y2)
        self.wiProfileY.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.wiProfileY.setObjectName("wiProfileY")
        self.widget = QtWidgets.QWidget(self.splitter_y2)
        self.widget.setMinimumSize(QtCore.QSize(200, 0))
        self.widget.setMaximumSize(QtCore.QSize(200, 200))
        self.widget.setObjectName("widget")
        self.horizontalLayout.addWidget(self.splitter_x)

        self.retranslateUi(FrameViewer)
        QtCore.QMetaObject.connectSlotsByName(FrameViewer)

    def retranslateUi(self, FrameViewer):
        _translate = QtCore.QCoreApplication.translate
        FrameViewer.setWindowTitle(_translate("FrameViewer", "Form"))
from widgets.image_view import ImageViewNoKeyboard
from widgets.projectionwidget import ProjectionWidget
import icons_rc
